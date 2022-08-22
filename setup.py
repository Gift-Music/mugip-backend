from os import path

from setuptools import find_packages, setup

wdir = path.abspath(path.dirname(__file__))

try:
    with open(path.join(wdir, "README.md"), encoding="utf-8") as f:
        long_description = f.read()
except FileNotFoundError:
    long_description = ""

install_requires = [
    "aiofiles==0.8.0",
    "alembic==1.7.4",
    "asyncpg==0.26.0",
    "boto3[crt]==1.24.7",
    "boto3-stubs[s3]==1.24.7",
    "fastapi==0.78.0",
    "GeoAlchemy2==0.12.1",
    "gunicorn==20.1.0",
    "httpx==0.21.3",
    "jsonschema==3.2.0",
    "lz4==3.1.3",
    "msgpack==1.0.2",
    "pillow==9.1.1",
    "pydantic[email]==1.9.1",
    "pyjwt[crypto]==2.4.0",
    "python-multipart==0.0.5",
    "redis==4.3.3",
    "setuptools-scm==6.4.2",
    "sqlalchemy[asyncio]==1.4.37",
    "starlette==0.19.1",
    "uvicorn[standard]==0.17.6",
    "uvloop==0.16.0",
]

dev_install_requires = [
    "asgi-lifespan==1.0.1",
    "autopep8==1.5.7",
    "bandit==1.7.0",
    "black==22.6.0",
    "flake8-bugbear==21.4.3",
    "flake8-datetimez==20.10.0",
    "flake8-isort==4.0.0",
    "flake8-logging-format==0.6.0",
    "flake8-quotes==3.2.0",
    "flake8==3.9.2",
    "mypy==0.961",
    "pytest-asyncio==0.15.1",
    "pytest-cov==3.0.0",
    "pytest-env==0.6.2",
    "pytest==6.2.4",
    "types-redis==4.2.6",
    "sqlalchemy2-stubs==0.0.2a23",
]


if __name__ in ("__main__", "builtins"):
    setup(
        name="mugip-backend",
        description="API server for Mugip",
        long_description=long_description,
        url="https://github.com/gift-music/mugip-backend",
        author="logpacket",
        author_email="bash@kakao.com",
        classifiers=[
            "Development Status :: 5 - Production/Stable",
            "Programming Language :: Python :: 3.10",
            "Programming Language :: Python :: Implementation :: CPython",
            "Operating System :: POSIX",
            "Operating System :: MacOS :: MacOS X",
        ],
        packages=find_packages(),
        python_requires=">=3.10, <3.11",
        use_scm_version=True,
        setup_requires=["setuptools_scm"],
        install_requires=install_requires,
        extras_require={"dev": dev_install_requires},
        package_data={},
    )
