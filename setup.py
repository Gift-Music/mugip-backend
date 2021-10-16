from os import path

from setuptools import find_packages, setup

wdir = path.abspath(path.dirname(__file__))

try:
    with open(path.join(wdir, 'README.md'), encoding='utf-8') as f:
        long_description = f.read()
except FileNotFoundError:
    long_description = ''

install_requires = [
    'aiofiles==0.7.0',
    'alembic==1.7.4',
    'email-validator==1.1.3',  # required by 'pydantic[email]' (https://github.com/pypa/pip/issues/9644)
    'fastapi==0.70.0',
    'gunicorn==20.1.0',
    'jsonschema==3.2.0',
    'lz4==3.1.3',
    'msgpack==1.0.2',
    'psycopg2-binary==2.9.1',
    'pydantic==1.8.2',
    'pyjwt==2.2.0',
    'redis==3.5.3',
    'setuptools-scm==6.0.1',
    'sqlalchemy==1.4.25',
    'starlette==0.16.0',
    'uvicorn[standard]==0.15.0',
    'uvloop==0.16.0',
    'elasticsearch-dsl==7.4.0',
]

dev_install_requires = [
    'autopep8==1.5.7',
    'bandit==1.7.0',
    'flake8-bugbear==21.4.3',
    'flake8-datetimez==20.10.0',
    'flake8-isort==4.0.0',
    'flake8-logging-format==0.6.0',
    'flake8-quotes==3.2.0',
    'flake8==3.9.2',
    'mypy==0.910',
    'pip-tools==6.2.0',
    'pytest-asyncio==0.15.1',
    'pytest-cov==2.12.1',
    'pytest-env==0.6.2',
    'pytest==6.2.4',
    'types-redis==3.5.6',
    'sqlalchemy-stubs==0.4',
]


if __name__ in ('__main__', 'builtins'):
    setup(
        name='mugip-backend',

        description='API server for Mugip',
        long_description=long_description,
        url='https://github.com/gift-music/mugip-backend',

        author='logpacket',
        author_email='bash@kakao.com',

        classifiers=[
            'Development Status :: 5 - Production/Stable',
            'Programming Language :: Python :: 3.10',
            'Programming Language :: Python :: Implementation :: CPython',
            'Operating System :: POSIX',
            'Operating System :: MacOS :: MacOS X'
        ],

        packages=find_packages(),

        python_requires='>=3.10, <3.11',

        use_scm_version=True,
        setup_requires=['setuptools_scm'],

        install_requires=install_requires,
        extras_require={'dev': dev_install_requires},

        package_data={}
    )
