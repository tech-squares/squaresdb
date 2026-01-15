Ansible Vault
=============

We use [Ansible Vault](https://docs.ansible.com/ansible/latest/user_guide/vault.html) for storing certain secrets, such as for external auth providers (MIT Touchstone/Shibboleth, Google OAuth2).

Alex has the password on `tapada`, 'zamosc`, and `durmitor`; if somebody else needs to run this Ansible playbook, either get it or remove the Vault-needing steps.

To generate a password:
```
python3 -c "import string, secrets; alphabet = string.ascii_letters + string.digits; print(''.join(secrets.choice(alphabet) for i in range(72)))" > vault/prod.pass
chmod og-rw vault/prod.pass
```

To encrypt a file:
```
ansible-vault encrypt --vault-id=prod@vault/prod.pass roles/squaresdb/files/saml.key 
```

To run Ansible:
```
ansible-playbook --vault-id=prod@vault/prod.pass -i inventory.yaml -l squares-google playbook.yaml
```

Choose the hosts you wish to update with `-l squares-google` (or `-l squares-dehnert` for Alex's test machine).
