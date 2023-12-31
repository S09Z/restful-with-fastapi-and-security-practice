from setuptools import setup, find_packages

setup(
    name='my_fastapi_project',
    version='0.1.0',
    author='Your Name',
    author_email='your.email@example.com',
    description='A FastAPI project',
    packages=find_packages(),
    install_requires=[
        'fastapi==0.68.0',
        'uvicorn==0.15.0',
        'python-jose[cryptography]==3.3.0',
        'prisma-client-py==0.7.0',
        'redis==4.0.2'
    ],
    python_requires='>=3.8',
)
