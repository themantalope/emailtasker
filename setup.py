from setuptools import setup


setup(name='emailtasker',
      version='0.0.dev0',
      description='package for checking, starting and stopping processes via email.',
      author="Matt Antalek",
      author_email="matthew.antalek@gmail.com",
      license="MIT",
      packages=["emailtasker"],
      scripts=['bin/emailtasker'])
