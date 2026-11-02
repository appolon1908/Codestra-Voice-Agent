import importlib.metadata
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def locked_packages(path):
    packages = {}
    active = None
    hashes = 0
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('--hash=sha256:'):
            if not re.fullmatch(r'--hash=sha256:[0-9a-f]{64}(?: \\)?', line) or active is None:
                raise ValueError('invalid or unbound artifact hash')
            hashes += 1
            continue
        if active is not None and not hashes:
            raise ValueError('runtime package lacks artifact hashes')
        match = re.fullmatch(r'([A-Za-z0-9_.-]+)==([^ ;\\]+)(?: \\)?', line)
        if not match:
            raise ValueError('only exact package pins and SHA-256 artifacts are allowed')
        active, version = match.groups()
        if active in packages:
            raise ValueError('duplicate runtime package')
        packages[active] = version
        hashes = 0
    if active is not None and not hashes:
        raise ValueError('runtime package lacks artifact hashes')
    return packages


class BuildContractTests(unittest.TestCase):
    def test_production_lock_is_complete_and_installed_versions_match(self):
        packages = locked_packages(ROOT / 'requirements.lock')
        self.assertGreaterEqual(len(packages), 3)
        for name, version in packages.items():
            with self.subTest(package=name):
                self.assertEqual(importlib.metadata.version(name), version)

    def test_ci_lock_retains_every_production_version(self):
        runtime = locked_packages(ROOT / 'requirements.lock')
        ci = locked_packages(ROOT / 'requirements-ci.lock')
        for name, version in runtime.items():
            with self.subTest(package=name):
                self.assertEqual(ci[name], version)

    def test_docker_build_requires_hashes_and_unprivileged_runtime(self):
        dockerfile = (ROOT / 'Dockerfile').read_text()
        self.assertIn('FROM python:3.13.18-slim@sha256:ae14d4ce8771606477a81446e7ef429edd6762305fc50c84507c1041fa8285d1', dockerfile)
        self.assertIn('COPY requirements.lock .', dockerfile)
        self.assertIn('pip install --no-cache-dir --require-hashes -r requirements.lock', dockerfile)
        self.assertIn('USER 10001:10001', dockerfile)
        self.assertIn('PYTHONDONTWRITEBYTECODE=1', dockerfile)
        self.assertNotIn('COPY . ', dockerfile)
        self.assertNotIn('ADD ', dockerfile)
        self.assertNotIn('requirements.txt', dockerfile)

if __name__ == '__main__':
    unittest.main()
