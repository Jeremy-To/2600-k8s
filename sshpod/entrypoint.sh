#!/bin/bash
echo "root:$ROOT_PASSWORD" | chpasswd
/usr/sbin/sshd -D
