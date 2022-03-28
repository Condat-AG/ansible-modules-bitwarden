# ansible-modules-bitwarden

Bitwarden integration for Ansible.

## Installation

The easiest way to install this lookup plugin is to use the
`ansible-galaxy` command:

    ansible-galaxy install git+https://github.com/c0sco/ansible-modules-bitwarden

This will place the `ansible-modules-bitwarden` role into
`$HOME/.ansible/roles`, where it will be available to all playbooks
you run on your system.

## Lookup plugin

To use this plugin, you will need to activate it by including the role
in your play.  For example:

    - hosts: localhost
      roles:
        - ansible-modules-bitwarden

Or add the modules directory to the lookup plugins environment variable

    `export ANSIBLE_LOOKUP_PLUGINS=/working-dirs/.roles/ansible-modules-bitwarden`

Use Ansible's `lookup()` function with the `bitwarden` argument,
followed by the items you want to retrieve. The default field is
`password`, but any other field can be specified using the `field`
named argument. If you need to specify the path to the Bitwarden CLI
binary, use the `path` named argument.

You can use `organization` and `collection` as optional properties 
to select a specific item in organization or collection.
You can use an id or a name.

## Examples

### Get a single password

```yaml
# Get password for Google
- debug:
    msg: {{ lookup('bitwarden', 'Google') }}
```

The above might result in:

```
TASK [debug] *********************************************************
ok: [localhost] => {
    "msg": "mysecret"
    }
```

### Get a single username

```yaml
# Get username for Google
- debug:
    msg: {{ lookup('bitwarden', 'Google', field='username') }}
```

The above might result in:

```
TASK [debug] *********************************************************
ok: [localhost] => {
    "msg": "alice"
    }
```
### See all available fields

```yaml
# Get all available fields for an entry
- debug:
    msg: {{ lookup('bitwarden', 'Google', field='item') }}
```

The above might result in:

```
TASK [debug] *********************************************************
ok: [localhost] => {
    "msg": {
        "favorite": false,
        "fields": [
            {
                "name": "mycustomfield",
                "type": 0,
                "value": "the value of my custom field"
            }
        ],
        "folderId": null,
        "id": "12345678-0123-4321-0000-a97001342c31",
        "login": {
            "password": "mysecret",
            "passwordRevisionDate": null,
            "totp": null,
            "username": "alice"
        },
        "name": "Google",
        "notes": null,
        "object": "item",
        "organizationId": "87654321-1234-9876-0000-a96800ed2b47",
        "revisionDate": "2018-10-19T19:20:17.923Z",
        "type": 1
    }
}
```
### Get the value of a custom field

```yaml
# Get the value of a custom field
- debug:
    msg: {{ lookup('bitwarden', 'Google', field='fields.mycustomfield') }}
```

The above might result in:

```
TASK [debug] *********************************************************
ok: [localhost] => {
    "msg": "the value of my custom field"
    }
```
Or, when muliple fields have the same name:
```
TASK [debug] *********************************************************
ok: [localhost] => {
    "msg": ["the value of my custom field", "second custom field with same name but different value"]
    }
```

### Get the value of a custom field in organization

```yaml
# Get the value of a custom field
- debug:
    msg: {{ lookup('bitwarden', 'Google', field='fields.mycustomfield', organization='My Company') }}
```

The above might result in:

```
TASK [debug] *********************************************************
ok: [localhost] => {
    "msg": "alice"
    }
```

### Get the value of a custom field in collection

```yaml
# Get the value of a custom field
- debug:
    msg: {{ lookup('bitwarden', 'Google', field='fields.mycustomfield', collection='My/Collection') }}
```

The above might result in:

```
TASK [debug] *********************************************************
ok: [localhost] => {
    "msg": "alice"
    }
```

### Get all values of a custom field

```yaml
# Get the value of a custom field
- debug:
    msg: {{ lookup('bitwarden', 'Google', field='fields') }}
```

The above might result in:

```
TASK [debug] *********************************************************
ok: [localhost] => {
    "msg": ["name": "custom_field_name", "value": "the value of my custom field"]
    }
```

### download attachment file

```yaml
# Get the value of a custom field
- debug:
    msg: {{ lookup('bitwarden', 'My Secure Credentials', attachments='privateKey.pem' ) }}
```
Optional parameters - output='/ansible/publicKey.pem' or output='/ansible/'

The above might result in:

```
TASK [debug] *********************************************************
ok: [localhost] => {
    "msg": "Saved /privateKey.pem"
    }
```

### download multiple attachment files into same directory

```yaml
# Get the value of a custom field
- debug:
    msg: {{ lookup('bitwarden', 'My Secure Credentials', attachments=['privateKey.pem', 'publicKey.pem'], output='/tmp/local' ) }}
```
The above might result in:
```
TASK [debug] *********************************************************
ok: [localhost] => {
    "msg": ["Saved /tmp/local/privateKey.pem", "Saved /tmp/local/publicKey.pem"]
    }
```
