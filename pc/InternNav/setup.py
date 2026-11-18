from pathlib import Path
from setuptools import setup, find_namespace_packages

setup(
    name="internnav", version="0.3.1",
    author="Intern Robotics", author_email="embodiedai@pjlab.org.cn",
    license="Apache 2.0",
    description="InternNav NextDiT real-world inference deployment",
    long_description=Path("README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    packages=find_namespace_packages(include=["internnav", "internnav.*"]),
    python_requires=">=3.10,<3.11",
    install_requires=["torch", "torchvision", "transformers", "diffusers", "flash-attn",
                      "numpy", "Pillow", "Flask", "einops", "opencv-python-headless"],
)
