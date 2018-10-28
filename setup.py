# coding=utf-8
import os
from time import sleep

cwd = os.getcwd() + "/"
path_script = os.path.join("/etc/linux-utils/", "fctrl/")

os.system("sudo mkdir /etc/linux-utils/")

os.system("sudo rm -R " + path_script)
os.system("sudo cp -r " + cwd + "fctrl " + "/etc/linux-utils/")


os.system("sudo chmod -R 775 " + path_script)

#shutil.copyfile("99fctrl", path_conf)
#os.chmod(path_conf, 0o775)

os.system("sudo cp " + cwd + "config-script.sh " + "/usr/bin/fctrl-config")
os.system("sudo chmod 755 /usr/bin/fctrl-config")

os.system("sudo cp " + cwd + "systemd " + "/etc/systemd/system/fctrl.service")
os.system("sudo chmod 755 /etc/systemd/system/fctrl.service")
os.system("sudo systemctl daemon-reload")
os.system("sudo systemctl enable fctrl")
os.system("sudo systemctl start fctrl")
sleep(1)
result = os.popen("sudo systemctl status fctrl").read()
print(result)
