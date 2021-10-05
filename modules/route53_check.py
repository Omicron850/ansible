from ansible.module_utils.basic import *

try:
    import boto3
    import re
except ImportError:
    HAS_BOTO = False
from botocore.client import ClientError

def check_route53(env, hosted_zone_id, stack_list, client):
    return_list = []
    for stack in stack_list:
        paginator = client.get_paginator('list_resource_record_sets')
        page_iterator = paginator.paginate(
            HostedZoneId=hosted_zone_id
        )
        for page in page_iterator:
            for record in page['ResourceRecordSets']:
                stack_name = re.sub("\d+", "", stack)
                stack_env = re.sub("%s"%env, "", stack_name)
                name_hyphen = re.sub("-", "", record['Name'])
                if record['Type'] == 'CNAME' and name_hyphen == '%s.%s.{{ domain }}.com.' % (stack_env,env):
                    stack_hyphen = re.sub("^[A-Za-z]+", "", stack)
                    stack_number = re.sub("%s"%env, "", stack_hyphen)
                    target_name = record['AliasTarget']['DNSName']
                    if stack_number in target_name:
                        return_list.append(target_name)
    return return_list

def main():

    module = AnsibleModule(
        argument_spec = dict(
            environment = dict(required=True, type='str'),
            zone_id = dict(required=True, type='str'),
            stacks_to_delete = dict(required=True, type='list')
            )
        )

    env = module.params['environment']
    hosted_zone_id = module.params['zone_id']
    stack_delete = module.params['stacks_to_delete']

    client = boto3.client('route53')

    stack_check = check_route53(env, hosted_zone_id, stack_delete, client)
    temp_json = {"stack_list": stack_check}
    module.exit_json(changed=False, meta=temp_json)

if __name__ == '__main__':
    main()