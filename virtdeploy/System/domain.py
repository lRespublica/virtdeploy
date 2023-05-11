import virtdeploy
import logging
import uuid
import libvirt
import subprocess

import virtdeploy.Utils.toml as toml
import virtdeploy.System.network as network

from virtdeploy.Utils.genmac import vid_provided
from virtdeploy.System.virt import conn


# Domains type info
# Begin
def getDomainTypesData():
    data = toml.getData(virtdeploy._dataPrefix + "/data/types.toml")
    if data is None:
        logging.fatal(f"Cannot find {virtdeploy._dataPrefix}/data/types.toml, please create it manually")
        return None

    return data


def getDomainTypeData(typeName):
    data = getDomainTypesData()
    return data.get(typeName)


def isDomainTypeExist(name):
    data = getDomainTypesData()
    return data.get(name) is not None


def addNewType(name, cpu, ram):
    data = {name: {"cpu": cpu, "ram": ram}}

    if isDomainTypeExist(name) is True:
        logging.warn(f"Cannot add {name} in {virtdeploy._dataPrefix}/data/types.toml. It`s already exists")
        return False

    return toml.write_to(virtdeploy._dataPrefix + "/data/types.toml", data)
# End


def createInitImage(domainDir):
    userData = f"{domainDir}/user-data.yaml"
    metaData = f"{domainDir}/meta-data.yaml"
    output = f"{domainDir}/seed.img"
    return subprocess.run(["cloud-localds", output, userData, metaData])


def resizeImage(iso, diskSize):
    return subprocess.run(["qemu-img", "resize", iso, diskSize])


def createBaseUserData(sshKey, file):
    userdata = f"""#cloud-config
users:
   - name: root
     ssh-authorized-keys:
       - {sshKey} user@any

growpart:
  mode: auto
  devices: ['/']
  ignore_growroot_disabled: false
"""

    with open(file, "w") as f:
        return f.write(userdata)


def createBaseMetaData(hostname, file):
    metadata = f"""
    instance-id: {hostname}
    local-hostname: {hostname}
    """

    with open(file, "w") as f:
        return f.write(metadata)


def createDomain(domainDir, domainType, number, net, ipNum, imageFilename):
    generated_uuid = uuid.uuid4()
    mac = vid_provided("52:54:00")

    netBridge = network.getNetworkBridge(net)
    netUuid = network.getNetworkUuid(net)
    netIp = network.getNetworkIp(net).split('.')

    netIp.pop()
    netIp.append(f"{ipNum}")
    domainIp = '.'.join(netIp)

    virNetwork = conn.networkLookupByName(net)

    domainTypeName = ""
    cpu = int()
    ram = int()
    for i in domainType:
        typeInfo = getDomainTypeData(i)
        domainTypeName += i
        cpu += (typeInfo.get("cpu"))
        ram += (typeInfo.get("ram"))
        disk = typeInfo.get("size")

    resizeImage(f"{domainDir}/{imageFilename}", disk)

    with open(f"{domainDir}/info.toml", "w") as f:
        f.write(f"[Network]\nuuid = {generated_uuid}\nmac = {mac}\nip = {domainIp}")

    xml = f"""
    <domain type='kvm' id='1'>
      <name>{net}-{domainTypeName}{number}</name>
      <uuid>{generated_uuid}</uuid>
      <memory unit='MiB'>{ram}</memory>
      <vcpu placement='static'>{cpu}</vcpu>
      <resource>
        <partition>/machine</partition>
      </resource>
      <os>
        <type arch='x86_64' machine='pc-q35-7.2'>hvm</type>
        <boot dev='hd'/>
      </os>
      <features>
        <acpi/>
        <apic/>
      </features>
      <cpu mode='host-passthrough' check='none' migratable='on'/>
      <clock offset='utc'>
        <timer name='rtc' tickpolicy='catchup'/>
        <timer name='pit' tickpolicy='delay'/>
        <timer name='hpet' present='no'/>
      </clock>
      <on_poweroff>destroy</on_poweroff>
      <on_reboot>restart</on_reboot>
      <on_crash>destroy</on_crash>
      <pm>
        <suspend-to-mem enabled='no'/>
        <suspend-to-disk enabled='no'/>
      </pm>
      <devices>
        <emulator>/usr/bin/qemu-system-x86_64</emulator>
        <disk type='file' device='disk'>
          <driver name='qemu' type='qcow2'/>
          <source file='{domainDir}/{imageFilename}' index='2'/>
          <backingStore/>
          <target dev='vda' bus='virtio'/>
          <alias name='virtio-disk0'/>
          <address type='pci' domain='0x0000' bus='0x04' slot='0x00' function='0x0'/>
        </disk>
        <disk type='file' device='cdrom'>
          <driver name='qemu' type='raw'/>
          <source file='{domainDir}/seed.img' index='1'/>
          <backingStore/>
          <target dev='sda' bus='sata'/>
          <readonly/>
          <alias name='sata0-0-0'/>
          <address type='drive' controller='0' bus='0' target='0' unit='0'/>
        </disk>
        <controller type='usb' index='0' model='qemu-xhci' ports='15'>
          <alias name='usb'/>
          <address type='pci' domain='0x0000' bus='0x02' slot='0x00' function='0x0'/>
        </controller>
        <controller type='pci' index='0' model='pcie-root'>
          <alias name='pcie.0'/>
        </controller>
        <controller type='pci' index='1' model='pcie-root-port'>
          <model name='pcie-root-port'/>
          <target chassis='1' port='0x10'/>
          <alias name='pci.1'/>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x02' function='0x0' multifunction='on'/>
        </controller>
        <controller type='pci' index='2' model='pcie-root-port'>
          <model name='pcie-root-port'/>
          <target chassis='2' port='0x11'/>
          <alias name='pci.2'/>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x02' function='0x1'/>
        </controller>
        <controller type='pci' index='3' model='pcie-root-port'>
          <model name='pcie-root-port'/>
          <target chassis='3' port='0x12'/>
          <alias name='pci.3'/>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x02' function='0x2'/>
        </controller>
        <controller type='pci' index='4' model='pcie-root-port'>
          <model name='pcie-root-port'/>
          <target chassis='4' port='0x13'/>
          <alias name='pci.4'/>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x02' function='0x3'/>
        </controller>
        <controller type='pci' index='5' model='pcie-root-port'>
          <model name='pcie-root-port'/>
          <target chassis='5' port='0x14'/>
          <alias name='pci.5'/>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x02' function='0x4'/>
        </controller>
        <controller type='pci' index='6' model='pcie-root-port'>
          <model name='pcie-root-port'/>
          <target chassis='6' port='0x15'/>
          <alias name='pci.6'/>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x02' function='0x5'/>
        </controller>
        <controller type='pci' index='7' model='pcie-root-port'>
          <model name='pcie-root-port'/>
          <target chassis='7' port='0x16'/>
          <alias name='pci.7'/>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x02' function='0x6'/>
        </controller>
        <controller type='pci' index='8' model='pcie-root-port'>
          <model name='pcie-root-port'/>
          <target chassis='8' port='0x17'/>
          <alias name='pci.8'/>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x02' function='0x7'/>
        </controller>
        <controller type='pci' index='9' model='pcie-root-port'>
          <model name='pcie-root-port'/>
          <target chassis='9' port='0x18'/>
          <alias name='pci.9'/>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x03' function='0x0' multifunction='on'/>
        </controller>
        <controller type='pci' index='10' model='pcie-root-port'>
          <model name='pcie-root-port'/>
          <target chassis='10' port='0x19'/>
          <alias name='pci.10'/>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x03' function='0x1'/>
        </controller>
        <controller type='pci' index='11' model='pcie-root-port'>
          <model name='pcie-root-port'/>
          <target chassis='11' port='0x1a'/>
          <alias name='pci.11'/>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x03' function='0x2'/>
        </controller>
        <controller type='pci' index='12' model='pcie-root-port'>
          <model name='pcie-root-port'/>
          <target chassis='12' port='0x1b'/>
          <alias name='pci.12'/>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x03' function='0x3'/>
        </controller>
        <controller type='pci' index='13' model='pcie-root-port'>
          <model name='pcie-root-port'/>
          <target chassis='13' port='0x1c'/>
          <alias name='pci.13'/>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x03' function='0x4'/>
        </controller>
        <controller type='pci' index='14' model='pcie-root-port'>
          <model name='pcie-root-port'/>
          <target chassis='14' port='0x1d'/>
          <alias name='pci.14'/>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x03' function='0x5'/>
        </controller>
        <controller type='sata' index='0'>
          <alias name='ide'/>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x1f' function='0x2'/>
        </controller>
        <controller type='virtio-serial' index='0'>
          <alias name='virtio-serial0'/>
          <address type='pci' domain='0x0000' bus='0x03' slot='0x00' function='0x0'/>
        </controller>
        <interface type='network'>
          <mac address='{mac}'/>
          <source network='{net}' portid='{netUuid}' bridge='{netBridge}'/>
          <target dev='vnet0'/>
          <model type='virtio'/>
          <alias name='net0'/>
          <address type='pci' domain='0x0000' bus='0x01' slot='0x00' function='0x0'/>
        </interface>
        <serial type='pty'>
          <source path='/dev/pts/2'/>
          <target type='isa-serial' port='0'>
            <model name='isa-serial'/>
          </target>
          <alias name='serial0'/>
        </serial>
        <console type='pty' tty='/dev/pts/2'>
          <source path='/dev/pts/2'/>
          <target type='serial' port='0'/>
          <alias name='serial0'/>
        </console>
        <input type='tablet' bus='usb'>
          <alias name='input0'/>
          <address type='usb' bus='0' port='1'/>
        </input>
        <input type='mouse' bus='ps2'>
          <alias name='input1'/>
        </input>
        <input type='keyboard' bus='ps2'>
          <alias name='input2'/>
        </input>
        <graphics type='vnc' port='5900' autoport='yes' listen='0.0.0.0'>
          <listen type='address' address='0.0.0.0'/>
        </graphics>
        <audio id='1' type='none'/>
        <video>
          <model type='virtio' heads='1' primary='yes'/>
          <alias name='video0'/>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x01' function='0x0'/>
        </video>
        <memballoon model='virtio'>
          <alias name='balloon0'/>
          <address type='pci' domain='0x0000' bus='0x05' slot='0x00' function='0x0'/>
        </memballoon>
        <rng model='virtio'>
          <backend model='random'>/dev/urandom</backend>
          <alias name='rng0'/>
          <address type='pci' domain='0x0000' bus='0x06' slot='0x00' function='0x0'/>
        </rng>
      </devices>
      <seclabel type='dynamic' model='dac' relabel='yes'>
        <label>+471:+36</label>
        <imagelabel>+471:+36</imagelabel>
      </seclabel>
    </domain>
    """
    domain = conn.defineXML(xml)
    try:
        domain.create()
        virNetwork.update(libvirt.VIR_NETWORK_UPDATE_COMMAND_ADD_LAST,
                          libvirt.VIR_NETWORK_SECTION_IP_DHCP_HOST, -1,
                          f"<host mac='{mac}' name='{domainTypeName}{number}' ip='{domainIp}'/>")
        return domain
    except libvirt.libvirtError as e:
        logging.fatal(repr(e))
        domain.undefine()
        conn.close()
        exit(1)
