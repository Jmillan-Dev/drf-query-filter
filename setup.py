import os
from setuptools import setup

file_path = os.path.dirname(__file__)
with open(os.path.join(file_path, 'README.md')) as f:
    long_description = f.read()
    
with open(os.path.join(file_path, 'requirements')) as f:
    install_requires = f.read().strip().splitlines()

setup(
    name='drf-query-filter',
    version='0.1.0.dev1',
    packages=['drf_query_filter'],
    description=(
        'A django app to apply filters on drf queryset '
        'using the query params with custom fields.'
    ),
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='',
    download_url='',
    license='',
    author='Josué Millán Zamora',
    author_email='hi@jmillan.me',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: TODO',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],
    install_requires=install_requires,
    keywords='drf-query-filter filters queryparameters django restframework',
)
