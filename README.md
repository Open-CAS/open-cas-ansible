# opencas-ansible
Collection of Ansible playbooks for setting up Open CAS accelerated devices.

## Configuration and usage
Default playbook configuration tries to configure Open CAS on `opencas-nodes`
host group from inventory.

### Configuring devices
Example configuration is shown in `group_vars/opencas-nodes.yml.sample`.
For default, out-of-the-box configuration you can only change the name to opencas-nodes.yml,
configure appropriate host groups and adjust the device names.

### Configuring IO-classes
Default configuration is already present at `roles/opencas-deploy/files/default.csv`.
Any additional ioclass config files present in this directory will be copied over to
configured hosts and may be used in cache devices configuration in group variables.

## Playbooks
### opencas-deploy
Installs Open CAS software on `opencas-node` group and configures caching devices
and cached volumes defined.

### opencas-teardown
Stops all cache instances and removes Open CAS software. Make sure that
`/dev/casx-y` devices aren't used at time of teardown.

## Roles
### opencas-validate
Validates the Open CAS configuration set (e.g. in `group_vars`).

### opencas-common
Makes sure that the installer is present on target host.

### opencas-defaults
Gathers custom facts needed for further processing, also in `defaults/main.yml`
there are some settings used by other roles.

### opencas-install
Installs Open CAS software.

### opencas-deploy
Copies over the IO-class configuration files, validates configuration and deploys
it on hosts.

