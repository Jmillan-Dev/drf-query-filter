import os
import setuptools

file_path = os.path.dirname(__file__)


def read_file(file_name: str):
    with open(os.path.join(file_path, file_name), encoding='utf-8') as f:
        return f.read()


long_description = read_file('README.md')
install_requires = read_file('requirements.txt').strip().splitlines()

setuptools.setup(
    name='drf-query-filter',
    version='0.1.7.1',
    packages=['drf_query_filter'],
    description=(
        'A django app to apply filters on drf queryset '
        'using the query params with custom fields.'
    ),
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/Jmillan-Dev/drf-query-filter',
    license='MIT License',
    author='Josué Millán Zamora',
    author_email='hi@jmillan.me',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Framework :: Django',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Topic :: Internet :: WWW/HTTP',
    ],
    install_requires=install_requires,
    keywords='drf-query-filter filters queryparameters django restframework',
)
