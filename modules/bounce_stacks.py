from ansible.module_utils.basic import AnsibleModule

try:
    import boto3

    HAS_BOTO = True
except ImportError:
    HAS_BOTO = False
from botocore.client import ClientError


def list_stacks(stacks, env, tag_name, tag_value):
    stack_list = stacks['Stacks']
    stack_reboot_list = []

    for stacks in stack_list:
        stack_name = stacks['StackName']
        Found = False
        StackState = False
        for tag in stacks['Tags']:
            if (tag['Key']).lower() == tag_name and (tag['Value']).lower() == tag_value:
                Found = True
            elif (tag['Key']).lower() == 'environment' and (tag['Value']).lower() == env:
                StackState = True
            elif (tag['Key']).lower() == tag_name and (tag['Value']).lower() == 'active'.lower():
                Found = True
        if Found == True and StackState == True:
            # Build a list of Stack Id's
            stack_reboot_list.append(stacks['StackId'])

    return stack_reboot_list


def list_instances(instances, stack_reboot_list):
    instance_reboot_list = []

    for r in instances['Reservations']:
        for inst in r['Instances']:
            #             #    print inst['InstanceId']
            if 'Tags' in inst.keys():
                for inst_tag in inst['Tags']:
                    if inst_tag['Key'] == 'aws:cloudformation:stack-id' and inst_tag['Value'] in stack_reboot_list:
                        instance_reboot_list.append(inst['InstanceId'])

    return instance_reboot_list


def reboot(ec2, instances, dry_run):
    # print str(instances)
    try:
        ec2.reboot_instances(InstanceIds=instances, DryRun=True)
    except ClientError as e:
        if 'DryRunOperation' not in str(e):
            return {"Error": "You don't have permission to reboot instances."}

    if not dry_run:
        try:
            response = ec2.reboot_instances(InstanceIds=instances, DryRun=dry_run)  # False
            reboot_result = dict(Success=str(response))
        except ClientError as e:
            reboot_result = dict(Error="Failed rebooting instance/s: " + str(e))

        return reboot_result


def main():
    module = AnsibleModule(
        argument_spec=dict(
            environment=dict(required=True, type='str'),
            tag_name=dict(required=True, type='str'),
            tag_value=dict(required=True, type='str'),
            dry_run=dict(required=False, type='str'),
            region=dict(required=False, type='str')
        )
    )

    env = module.params['environment']
    tag_name = module.params['tag_name']
    tag_value = module.params['tag_value']
    dry_run = module.params['dry_run']
    if dry_run.lower() == 'true':
        dry_run = True
    elif dry_run.lower() == 'false':
        dry_run = False
    region = module.params['region']

    cloudformation = boto3.client('cloudformation')
    stacks = cloudformation.describe_stacks()
    stack_reboot_list = list_stacks(stacks, env, tag_name, tag_value)

    ec2 = boto3.client('ec2')
    instances = ec2.describe_instances()
    instance_reboot_list = list_instances(instances, stack_reboot_list)
    reboot_result = reboot(ec2, instance_reboot_list, dry_run)
    # print str(reboot_result)

    module.exit_json(changed=False, stack_reboot_list=stack_reboot_list, instance_reboot_list=instance_reboot_list,
                     reboot_result=reboot_result)


if __name__ == '__main__':
    main()