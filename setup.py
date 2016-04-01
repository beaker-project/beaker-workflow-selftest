from setuptools import setup, find_packages
setup(
    name='beaker-workflow-selftest',
    version='1.0',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    entry_points={
        'bkr.client.commands': [
            'workflow-selftest = beaker_workflow_selftest:Workflow_SelfTest',
        ],
    },
)
