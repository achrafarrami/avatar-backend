"""Minimal MICA inference network, vendored from Zielon/MICA (MPG license —
research/non-commercial; see models/ headers in that repo).

We reproduce ONLY the two trained submodules whose weights live in mica.tar
so the checkpoint loads with matching keys:
  - IResNet-100 ArcFace backbone  (checkpoint key 'arcface')
  - MappingNetwork regressor       (checkpoint key 'flameModel.regressor.*')

The FLAME decoder is NOT reproduced: MICA emits the NEUTRAL canonical shape
(expression = 0, pose = 0), for which the full FLAME/LBS forward collapses to
    verts = v_template + shapedirs[:, :, :300] @ betas
and v_template + shapedirs are themselves stored in the checkpoint
('flameModel.generator.v_template' / '.shapedirs'). So there is no runtime
dependency on generic_model.pkl, chumpy, scipy, lbs.py, or pytorch3d.

The IResNet/MappingNetwork code is copied verbatim (minus the CUDA autocast
wrapper, which is a no-op for us) so the state_dicts load 1:1.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


def _conv3x3(inp, outp, stride=1, groups=1, dilation=1):
    return nn.Conv2d(inp, outp, 3, stride, dilation, groups=groups,
                     bias=False, dilation=dilation)


def _conv1x1(inp, outp, stride=1):
    return nn.Conv2d(inp, outp, 1, stride, bias=False)


class IBasicBlock(nn.Module):
    expansion = 1

    def __init__(self, inplanes, planes, stride=1, downsample=None,
                 groups=1, base_width=64, dilation=1):
        super().__init__()
        self.bn1 = nn.BatchNorm2d(inplanes, eps=1e-05)
        self.conv1 = _conv3x3(inplanes, planes)
        self.bn2 = nn.BatchNorm2d(planes, eps=1e-05)
        self.prelu = nn.PReLU(planes)
        self.conv2 = _conv3x3(planes, planes, stride)
        self.bn3 = nn.BatchNorm2d(planes, eps=1e-05)
        self.downsample = downsample
        self.stride = stride

    def forward(self, x):
        identity = x
        out = self.bn1(x)
        out = self.conv1(out)
        out = self.bn2(out)
        out = self.prelu(out)
        out = self.conv2(out)
        out = self.bn3(out)
        if self.downsample is not None:
            identity = self.downsample(x)
        out += identity
        return out


class IResNet(nn.Module):
    """iResNet-100 (layers [3, 13, 30, 3]), 112x112 -> 512 features."""
    fc_scale = 7 * 7

    def __init__(self, layers=(3, 13, 30, 3), num_features=512):
        super().__init__()
        self.inplanes = 64
        self.dilation = 1
        self.conv1 = nn.Conv2d(3, 64, 3, 1, 1, bias=False)
        self.bn1 = nn.BatchNorm2d(64, eps=1e-05)
        self.prelu = nn.PReLU(64)
        self.layer1 = self._make_layer(64, layers[0], stride=2)
        self.layer2 = self._make_layer(128, layers[1], stride=2)
        self.layer3 = self._make_layer(256, layers[2], stride=2)
        self.layer4 = self._make_layer(512, layers[3], stride=2)
        self.bn2 = nn.BatchNorm2d(512, eps=1e-05)
        self.dropout = nn.Dropout(p=0, inplace=True)
        self.fc = nn.Linear(512 * self.fc_scale, num_features)
        self.features = nn.BatchNorm1d(num_features, eps=1e-05)
        self.features.weight.requires_grad = False

    def _make_layer(self, planes, blocks, stride=1):
        downsample = None
        if stride != 1 or self.inplanes != planes:
            downsample = nn.Sequential(
                _conv1x1(self.inplanes, planes, stride),
                nn.BatchNorm2d(planes, eps=1e-05))
        layers = [IBasicBlock(self.inplanes, planes, stride, downsample)]
        self.inplanes = planes
        for _ in range(1, blocks):
            layers.append(IBasicBlock(self.inplanes, planes))
        return nn.Sequential(*layers)

    def forward(self, x):
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.prelu(x)
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)
        x = self.bn2(x)
        x = torch.flatten(x, 1)
        x = self.dropout(x)
        x = self.fc(x)
        x = self.features(x)
        return x


class MappingNetwork(nn.Module):
    """512 -> 300 shape regressor (z_dim=512, hidden_dim=300, hidden=3)."""

    def __init__(self, z_dim=512, hidden_dim=300, out_dim=300, hidden=3):
        super().__init__()
        self.skips = [int(hidden / 2)] if hidden > 5 else []
        self.network = nn.ModuleList(
            [nn.Linear(z_dim, hidden_dim)] +
            [nn.Linear(hidden_dim, hidden_dim) if i not in self.skips
             else nn.Linear(hidden_dim + z_dim, hidden_dim)
             for i in range(hidden)])
        self.output = nn.Linear(hidden_dim, out_dim)

    def forward(self, z):
        h = z
        for i, layer in enumerate(self.network):
            h = layer(h)
            h = F.leaky_relu(h, negative_slope=0.2)
            if i in self.skips:
                h = torch.cat([z, h], 1)
        return self.output(h)


class MicaNet(nn.Module):
    """arcface blob (B,3,112,112) -> neutral FLAME vertices (B,5023,3)."""

    def __init__(self):
        super().__init__()
        self.arcface = IResNet()
        self.regressor = MappingNetwork()
        self.register_buffer("v_template", torch.zeros(5023, 3))
        self.register_buffer("shapedirs", torch.zeros(5023, 3, 300))
        # iBUG-68 landmark embedding (barycentric on faces), from checkpoint
        self.register_buffer("faces_t", torch.zeros(9976, 3, dtype=torch.long))
        self.register_buffer("lmk_faces_idx", torch.zeros(1, 68, dtype=torch.long))
        self.register_buffer("lmk_bary", torch.zeros(1, 68, 3))

    @torch.no_grad()
    def forward(self, blob):
        code = F.normalize(self.arcface(blob))
        betas = self.regressor(code)                      # (B, 300)
        disp = torch.einsum("vcl,bl->bvc", self.shapedirs, betas)
        return self.v_template.unsqueeze(0) + disp

    @torch.no_grad()
    def landmarks68(self, verts):
        """verts (B,5023,3) -> iBUG-68 3D landmarks (B,68,3) by barycentric
        interpolation on the landmark faces (FLAME.compute_landmarks)."""
        b, v = verts.shape[0], verts.shape[1]
        idx = self.lmk_faces_idx.expand(b, -1)            # (B,68)
        tri = self.faces_t[idx.reshape(-1)].reshape(b, 68, 3)
        tri = tri + (torch.arange(b) * v).view(b, 1, 1)
        lmk_v = verts.reshape(-1, 3)[tri]                 # (B,68,3,3)
        return torch.einsum("blfi,blf->bli", lmk_v, self.lmk_bary.expand(b, -1, -1))

    @classmethod
    def from_checkpoint(cls, ckpt_path, device="cpu"):
        ckpt = torch.load(ckpt_path, map_location=device, weights_only=False)
        net = cls()
        net.arcface.load_state_dict(ckpt["arcface"])
        fm = ckpt["flameModel"]
        net.regressor.load_state_dict(
            {k[len("regressor."):]: v for k, v in fm.items()
             if k.startswith("regressor.")})
        net.v_template.copy_(fm["generator.v_template"])
        net.shapedirs.copy_(fm["generator.shapedirs"][:, :, :300])
        net.faces_t.copy_(fm["generator.faces_tensor"].long())
        net.lmk_faces_idx.copy_(fm["generator.full_lmk_faces_idx"].long())
        net.lmk_bary.copy_(fm["generator.full_lmk_bary_coords"].float())
        net.faces = fm["generator.faces_tensor"].cpu().numpy()
        net.eval().to(device)
        return net
