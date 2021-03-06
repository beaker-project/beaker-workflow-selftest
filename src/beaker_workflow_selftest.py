from bkr.client import BeakerWorkflow, BeakerJob, BeakerRecipeSet, BeakerRecipe

ext4_unsupported_distros = ['RHEL4-U9', 'RHEL5.11-Server-20140827.0', 'RHEL5.11-Client-20140827.0']
beah_default_distros = [
    'RHEL4-U9',
    'RHEL5.11-Server-20140827.0',
    'RHEL5.11-Client-20140827.0',
    'RHEL-6.9-20170309.0',
    'RHEL-7.2-20151030.0',
    'RHEL-7.3-20161019.0',
    'Fedora-27',
    'Fedora-28',
]

def distros_variants_arches_harness(multihost=False):
    """
    For single-host testing we return all combinations of
    (distro, variant, architecture, harness) which are fully supported for the 
    purposes of Beaker acceptance testing. Note that there are other platforms 
    and releases which are expected to work but are not important enough to 
    block a Beaker release (for example: RHEL3, EOL Fedora releases).

    For multi-host testing we only return a much smaller subset of the 
    supported combinations, because 3 recipes of every combination would be too 
    expensive.

    Empty string for the harness means "use the default".
    """
    supported_combinations = [
        ('RHEL4-U9', [
            ('AS', ['i386', 'x86_64', 'ppc64', 's390', 's390x']),
            #('ES', ['i386', 'x86_64']),
            #('WS', ['i386', 'x86_64']),
            #('Desktop', ['i386', 'x86_64']),
        ]),
        ('RHEL5.11-Server-20140827.0', [
            ('', ['i386', 'x86_64', 'ppc64', 's390x']),
        ]),
        ('RHEL5.11-Client-20140827.0', [
            ('', ['i386', 'x86_64']),
        ]),
        ('RHEL-6.9-20170309.0', [
            ('Server', ['i386', 'x86_64', 'ppc64', 's390x']),
            ('Workstation', ['i386', 'x86_64']),
            ('Client', ['i386', 'x86_64']),
            ('ComputeNode', ['x86_64']),
        ]),
        ('RHEL-7.2-20151030.0', [
            ('Server', ['x86_64', 'ppc64', 'ppc64le', 's390x', 'aarch64']),
            ('Client', ['x86_64']),
            ('Workstation', ['x86_64']),
            ('ComputeNode', ['x86_64']),
        ]),
        ('RHEL-7.3-20161019.0', [
            ('Server', ['x86_64', 'ppc64', 'ppc64le', 's390x', 'aarch64']),
            ('Client', ['x86_64']),
            ('Workstation', ['x86_64']),
            ('ComputeNode', ['x86_64']),
        ]),
        # RHEL8 Alpha
        ('RHEL-8.0-20180531.2', [
            ('BaseOS', ['x86_64', 'ppc64le', 's390x', 'aarch64']),
        ]),
        # snap1
        ('RHEL-8.0-20180920.2', [
            ('BaseOS', ['x86_64', 'ppc64le', 's390x', 'aarch64']),
        ]),
        ('Fedora-27', [
            ('Server', ['i386', 'x86_64', 'ppc64', 'ppc64le', 'aarch64', 's390x']),
            ('Workstation', ['i386', 'x86_64']),
        ]),
        ('Fedora-28', [
            ('Server', ['i386', 'x86_64', 'ppc64', 'ppc64le', 'aarch64', 's390x']),
            ('Workstation', ['i386', 'x86_64']),
        ]),
    ]
    for distro, variants_arches in supported_combinations:
        for variant, arches in variants_arches:
            if not multihost:
                for arch in arches:
                    yield (distro, variant, arch, '')
            else:
                # This is the simplest option since x86_64 is supported in 
                # every release and is the most abundant type of hardware. We 
                # *could* do something smarter like use a different arch from 
                # each distro-variant in order to broaden the coverage.
                yield (distro, variant, 'x86_64', '')
            if distro in beah_default_distros:
                # Repeat the above, but opting in to Restraint instead.
                if not multihost:
                    for arch in arches:
                        yield (distro, variant, arch, 'restraint-rhts')
                else:
                    yield (distro, variant, 'x86_64', 'restraint-rhts')

class Workflow_SelfTest(BeakerWorkflow):
    """Workflow to generate a job for testing Beaker itself"""
    enabled = True

    def options(self):
        super(Workflow_SelfTest, self).options()

        # Remove unneeded inherited parser options
        self.parser.remove_option('--family')
        self.parser.remove_option('--tag')
        self.parser.remove_option('--task')
        self.parser.remove_option('--package')
        self.parser.remove_option('--task-type')
        self.parser.remove_option('--servers')
        self.parser.remove_option('--clients')

    def recipe(self, harness, distro, variant, arch, task_names, role='STANDALONE', **kwargs):
        ks_meta = kwargs.pop('ks_meta') or ''
        extra_whiteboard = ''
        if 'Fedora' in distro:
            ks_meta += ' no_updates_repos'
        if harness:
            extra_whiteboard = '(harness=%s)' % harness
            ks_meta += ' harness=%s' % harness
        recipe = BeakerRecipe(**kwargs)
        recipe.addBaseRequires(distro=distro, variant=variant, ks_meta=ks_meta, **kwargs)
        arch_require = self.doc.createElement('distro_arch')
        arch_require.setAttribute('op', '=')
        arch_require.setAttribute('value', arch)
        return self.processTemplate(recipe,
                requestedTasks=[{'name': task_name, 'arches': []} for task_name in task_names],
                distroRequires=[arch_require],
                whiteboard='%s %s %s %s %s' % (distro, variant, arch, role, extra_whiteboard),
                role=role,
                **kwargs)

    def run(self, *args, **kwargs):
        whiteboard = kwargs.pop('whiteboard')
        # We treat these options as filters, meaning if nothing is given we 
        # will run all possible combinations.
        kwargs.pop('family')
        requested_distro = kwargs.pop('distro')
        requested_variant = kwargs.pop('variant')
        requested_arches = kwargs.pop('arches')

        self.set_hub(**kwargs)

        job = BeakerJob(whiteboard=whiteboard, **kwargs)

        for distro, variant, arch, harness in distros_variants_arches_harness(multihost=False):
            if requested_distro and requested_distro != distro:
                continue
            if requested_variant and requested_variant != variant:
                continue
            if requested_arches and arch not in requested_arches:
                continue
            task_names = [
                '/distribution/beaker/Sanity/Skip-result',
                '/distribution/beaker/Sanity/reboot-tests',
            ]
            if distro not in ext4_unsupported_distros:
                task_names.append('/CoreOS/examples/Sanity/ext4-test')
            recipe = self.recipe(harness, distro, variant, arch, task_names=task_names, **kwargs)
            job.addRecipe(recipe)

        for distro, variant, arch, harness in distros_variants_arches_harness(multihost=True):
            if requested_distro and requested_distro != distro:
                continue
            if requested_variant and requested_variant != variant:
                continue
            if requested_arches and arch not in requested_arches:
                continue

            rs = BeakerRecipeSet(**kwargs)
            for role in ['SERVERS', 'CLIENTONE', 'CLIENTTWO']:
                recipe = self.recipe(harness, distro, variant, arch,
                        task_names=['/distribution/beaker/Sanity/sync-set_block-tests'],
                        role=role, **kwargs)
                rs.addRecipe(recipe)
            job.addRecipeSet(rs)

        jobxml = job.toxml(**kwargs)
        if kwargs.get('debug', False):
            print job.node.toprettyxml()
        if not kwargs.get('dryrun', False):
            t_id = self.hub.jobs.upload(jobxml)
            print 'Submitted: %s' % [t_id]
