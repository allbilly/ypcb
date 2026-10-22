"""Resolve checkout and tool locations without embedding a developer's home.

External tools may be supplied through the environment or discovered on PATH.
Bonetto overrides take precedence over legacy OpenTPU aliases. Workspace
donors default to the user's home directory, matching fedora-env.sh.
"""
import os
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def _env_path(name, default):
    return Path(os.environ.get(name) or str(default)).expanduser()


def vivado_bin():
    explicit = (os.environ.get('BONETTO_VIVADO_BIN') or
                os.environ.get('OTPU_VIVADO_BIN') or os.environ.get('VIVADO_BIN'))
    if explicit:
        return Path(explicit).expanduser()
    root = os.environ.get('VIVADO_ROOT') or os.environ.get('XILINX_VIVADO')
    if root:
        return Path(root).expanduser() / 'bin'
    binary = shutil.which('vivado')
    if binary:
        return Path(binary).resolve().parent
    # Support the common per-user installation without assuming a username.
    installed = sorted((Path.home() / 'vivado').glob('*/Vivado/bin/vivado'))
    return installed[-1].parent if installed else Path('vivado-bin')


def yosys_share():
    explicit = os.environ.get('BONETTO_YOSYS_SHARE') or os.environ.get('OTPU_YOSYS_SHARE')
    if explicit:
        return Path(explicit).expanduser()
    binary = shutil.which(os.environ.get('BONETTO_YOSYS') or os.environ.get('OTPU_YOSYS', 'yosys'))
    if binary:
        for executable in [Path(binary), Path(binary).resolve()]:
            share = executable.parent.parent / 'share/yosys'
            if share.is_dir():
                return share
    return ROOT / 'build/deps/yosys/share/yosys'


def expand_paths(text):
    """Expand location tokens in a path or a generated tool command."""
    workspace = _env_path('BONETTO_WORKSPACE_ROOT',
                          os.environ.get('OTPU_WORKSPACE_ROOT') or Path.home())
    ypcb = _env_path('YPCB_ROOT', workspace / 'ypcb')
    values = {
        '@REPO@': lambda: ROOT,
        '@WORKSPACE@': lambda: workspace,
        '@YPCB@': lambda: ypcb,
        '@VIVADO_LAB_ROOT@': lambda: _env_path('VIVADO_LAB_ROOT', Path.home() / 'vivado/2026.1.1/Vivado_Lab'),
        '@VIVADO_BIN@': vivado_bin,
        '@VIVADO_ROOT@': lambda: vivado_bin().parent,
        '@YOSYS@': lambda: os.environ.get('BONETTO_YOSYS') or os.environ.get('OTPU_YOSYS') or shutil.which('yosys') or 'yosys',
        '@YOSYS_SHARE@': yosys_share,
        '@SLANG@': lambda: _env_path('BONETTO_SLANG', os.environ.get('OTPU_SLANG') or workspace / 'etsoc/out/fpga/tools/sv-elab-build/slang.so'),
    }
    for token, resolve in values.items():
        if token in text:
            text = text.replace(token, str(resolve()))
    return text
