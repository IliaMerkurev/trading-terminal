"""Build/run this checkout using the calling Python, without changing shell policies."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',action='store_true')
    parser.add_argument('--no-launch',action='store_true')
    parser.add_argument('--data-root',type=Path)
    parser.add_argument('--cargo-home',type=Path)
    parser.add_argument('--target-dir',type=Path,help='Separate Cargo build output; also used when launching')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    env=os.environ.copy()
    env['TRADING_TERMINAL_PYTHON']=sys.executable
    target=Path(args.target_dir or env.get('CARGO_TARGET_DIR') or root/'src-tauri/target').resolve()
    if args.target_dir:env['CARGO_TARGET_DIR']=str(target)
    if args.data_root:
        if not args.data_root.is_absolute():parser.error('--data-root must be absolute')
        env['TRADING_TERMINAL_DATA_ROOT']=str(args.data_root)
    if args.cargo_home:env['CARGO_HOME']=str(args.cargo_home.resolve())
    elif (root/'.local-tools/cargo-home').exists():env['CARGO_HOME']=str(root/'.local-tools/cargo-home')
    subprocess.run([sys.executable,'scripts/verify_runtime.py'],cwd=root,env=env,check=True)
    if args.build:
        node=shutil.which('node');cargo=shutil.which('cargo')
        if not node or not cargo:parser.error('Node and Cargo must be available in this process PATH')
        subprocess.run([node,'scripts/frontend.mjs','build'],cwd=root,env=env,check=True)
        subprocess.run([cargo,'build','--offline','--locked','--features','custom-protocol','--manifest-path','src-tauri/Cargo.toml'],cwd=root,env=env,check=True)
    executable=target/'debug/trading-terminal.exe'
    if not args.no_launch:
        if not executable.exists():parser.error('This checkout has not been built; use --build first')
        subprocess.Popen([str(executable)],cwd=root,env=env,creationflags=subprocess.CREATE_NO_WINDOW)


if __name__=='__main__':main()
