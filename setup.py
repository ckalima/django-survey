from setuptools import setup, find_packages

setup(
    name='django-survey',
    version='1.1.1',
    description='A simple extensible survey application for django sites. Forked from django-survey.',
    author='Chris Kalima',
    author_email='chris@marinexplore.com',
    url='https://github.com/ckalima/django-survey',
    packages=find_packages(),
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Django',
    ],
    include_package_data=True,
    zip_safe=False,
)
