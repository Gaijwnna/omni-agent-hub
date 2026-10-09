import subprocess,pathlib
files=subprocess.check_output(['git','ls-files'],text=True,cwd=pathlib.Path(__file__).resolve().parents[2]).splitlines()
bad=[p for p in files if pathlib.Path(p).name=='.env' or p.endswith(('.pem','.key','.db'))]
if bad:raise SystemExit('Sensitive runtime files are tracked: '+', '.join(bad))
print('No runtime secret-file extensions tracked. Run a full secret scanner in your repository as well.')
