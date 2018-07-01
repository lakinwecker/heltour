"""A slimmed down version of something I use at work.

Mostly just some helpers to go with baste and fabric to manage a project.

TODO: yes, we could probably use gulp or some other fancy new fangled project,
but I'm not familiar with any of them so I probalby won't set it up. Feel free to.
"""

from commands import getoutput
import datetime
import os.path

from fabric.api import (
    local, settings, hosts, get, run, put, hide
)
from fabric import colors
from fabric.contrib.console import confirm

from baste import (
    project_relative,
    RsyncMedia,
    RsyncDeployment,
    UbuntuPgCreateDbAndUser,
    PgLoadPlain,
)


#-------------------------------------------------------------------------------
def python_dependency(package, python_version, dir=None):
    """Adds the given package as a dependency for the given python version."""

    # Figure out the directory we'll be symlinking to.
    if dir is None:
        base_dir = project_relative(package)
        if os.path.exists(os.path.join(base_dir, "__init__.py")):
            dir = os.path.join(base_dir, '..')
        elif os.path.exists(os.path.join(base_dir, package, "__init__.py")):
            dir = base_dir
        elif os.path.exists(os.path.join(base_dir, 'src', package, "__init__.py")):
            dir = os.path.join(base_dir, 'src')

    pth_file = "env/lib/%s/site-packages/%s.pth" % (python_version, package)
    pth_file = project_relative(pth_file)
    python_path = dir
    create_pth_file = "echo \"%s\" > %s" % (python_path, pth_file)
    print(colors.green("[install] ") + package)
    with hide('running'):
        local("rm %s; %s" % (pth_file, create_pth_file))

#-------------------------------------------------------------------------------
def update(all_repos, python_repos, python_package_name, python_version):
    """
    Update all of the dependencies to their latest versions.
    """
    for repo in all_repos.values():
        repo.update()

    for repo in python_repos.values():
        python_dependency(repo.name, python_version)
    python_dependency(python_package_name, python_version)

#-------------------------------------------------------------------------------
def createdb(python_package_name, database_name, database_user):
    print(
        colors.green("Look up the password to set for the user with: ") +
        colors.blue("cat %s/live_settings.py | grep \"PASSWORD\"" % python_package_name)
    )
    if confirm(colors.red("You should only run this when others aren't looking over your shoulder. Run the command?")):
        local("cat %s/live_settings.py | grep \"PASSWORD\"" % python_package_name)
    if confirm(colors.red("This will overwrite local data, are you sure?")):
        UbuntuPgCreateDbAndUser(database_name, database_user)()

#-------------------------------------------------------------------------------
def upload_sshkey(password_file_name, ssh_key_path):
    run("mkdir -p ~/.ssh")
    local_key = "~/.ssh/id_rsa.pub"
    target = "%s/id_rsa.pub" % ssh_key_path
    put(local_key, target)
    run("cat ~/id_rsa.pub >> .ssh/authorized_keys")
    run("chmod 0700 .ssh")
    run("chmod 0600 .ssh/*")
    run("rm ~/id_rsa.pub")


#-------------------------------------------------------------------------------
def latest_live_media(live_media_path, local_media_path, password_file_name, live_ssh_username, live_domain):
    local_dir = local_media_path
    remote_dir = live_media_path
    if confirm(colors.red("This will overwrite local data, are you sure?")):
        RsyncMedia(
            '%s@%s' % (live_ssh_username, live_domain),
            remote_directory=remote_dir,
            local_directory=local_dir
        )()

#-------------------------------------------------------------------------------
def latest_live_db(live_backup_script_path, live_latest_sql_file_path, python_package_name, database_name, database_user):
    if confirm(colors.red("This will overwrite local data, are you sure?")):
        if confirm(colors.red("Create a new backup?")):
            run(live_backup_script_path)
        local_target = project_relative("data/latestdb.sql.bz2")
        if confirm(colors.red("Download New backup?")):
            local_db = get(live_latest_sql_file_path, local_target)[0]
        else:
            local_db = local_target
        with settings(warn_only=True):
            if confirm(colors.red("You should only run this when others aren't looking over your shoulder. Show database password?")):
                local("cat %s/live_settings.py | grep \"PASSWORD\"" % python_package_name)
            PgLoadPlain(local_db, database_name, database_user)()

