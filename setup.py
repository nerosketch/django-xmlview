from setuptools import setup

import xmlview


setup(
    name='django-xmlview',
    version=xmlview.__version__,
    description='Return XML from python dicts. '
                'Created based on https://github.com/jsocol/django-jsonview.git',
    author='Dmitry Novikov',
    author_email='nerosketch@gmail.com',
    url='https://github.com/nerosketch/django-xmlview',
    zip_safe=False,
    classifiers=[
        'Development Status :: 1 - Planning',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: Freeware',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
)
