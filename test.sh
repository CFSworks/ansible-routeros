#!/bin/bash

set -euo pipefail
cd ${0%/*}

# Establish working directory
mkdir -p temp/
cd temp/

# Make sure Mikrotik CHR is downloaded
if [ ! -e chr.vdi ]; then
	wget -O chr.vdi https://download2.mikrotik.com/routeros/6.38.1/chr-6.38.1.vdi
fi

# Create snapshot image for testing
if [ -f chr.qcow2 ]; then rm chr.qcow2; fi
qemu-img create -f qcow2 -b chr.vdi chr.qcow2

# Start RouterOS
qemu-system-x86_64 -hda chr.qcow2 -nographic -device e1000,netdev=net0 \
                   -netdev user,id=net0,net=192.168.254.0/24,dhcpstart=192.168.254.10,hostfwd=tcp:127.0.0.1:8728-:8728,hostfwd=tcp:127.0.0.1:22122-:22 > /dev/null &
QEMU_PID=%%
cleanup() {
	kill $QEMU_PID
}
trap cleanup EXIT

# Wait for it to become available
echo Waiting for RouterOS to boot...
python -c "while True:
    try: __import__('librouteros').connect('127.0.0.1','admin','')
    except: continue
    else: break"
echo ...DONE

# Generate an inventory file
cat > inventory <<EOF
[routeros:vars]
api='{ "host": "{{ inventory_hostname }}", "username": "admin", "password": "", "transport": "api" }'
cli='{ "host": "{{ inventory_hostname }}", "port": 22122, "username": "admin", "password": "", "transport": "cli" }'

[routeros]
localhost ansible_connection=local ansible_python_interpreter=$(which python)
EOF

# Fire off Ansible
cd ..
export ANSIBLE_LIBRARY=$PWD/library
export PYTHONPATH=$ANSIBLE_LIBRARY
ansible-playbook -i temp/inventory test/integration/routeros.yaml
