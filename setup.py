from setuptools import setup, find_packages

setup(
    name='django-survey',
    version='0.0.3',
    description='A simple extensible survey application for django sites. Forked from django-survey.',
    author='Chris Kalima',
    author_email='chris@marinexplore.com',
    url='https://github.com/ckalima/django-survey',
    packages=find_packages(),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Django',
    ],
    include_package_data=True,
    zip_safe=False,
)
