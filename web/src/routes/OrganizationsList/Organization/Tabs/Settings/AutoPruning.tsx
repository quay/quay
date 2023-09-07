import { ActionGroup, Button, Flex, Form, FormGroup, FormSelect, FormSelectOption, NumberInput, TextInput } from "@patternfly/react-core";
import { useEffect, useState } from "react";
import Conditional from "src/components/empty/Conditional";
import { useCreateNamespaceAutoPrunePolicy, useDeleteNamespaceAutoPrunePolicy, useNamespaceAutoPrunePolicies, useUpdateNamespaceAutoPrunePolicy } from "src/hooks/UseOrganization";
import { isNullOrUndefined } from "src/libs/utils";
import { AutoPruneMethod, NamespaceAutoPrunePolicy } from "src/resources/OrganizationResource";


export default function AutoPruning(props: AutoPruning){
    const [uuid, setUuid] = useState<string>(null); 
    const [method, setMethod] = useState<AutoPruneMethod>(AutoPruneMethod.NONE);
    const [tagCount, setTagCount] = useState<number>(0);
    const [tagAge, setTagAge] = useState<string>("7d");
    const {
        error,
        isSuccess: successFetchingPolicies,
        isLoading, 
        policies,
    } = useNamespaceAutoPrunePolicies(props.org);
    const {
        createPolicy,
        successCreatePolicy,
        errorCreatePolicy,
    } = useCreateNamespaceAutoPrunePolicy(props.org);
    const {
        updatePolicy,
        successUpdatePolicy,
        errorUpdatePolicy,
    } = useUpdateNamespaceAutoPrunePolicy(props.org);
    const {
        deletePolicy,
        successDeletePolicy,
        errorDeletePolicy,
    } = useDeleteNamespaceAutoPrunePolicy(props.org);

    useEffect(()=>{
      if(successFetchingPolicies){
          // Currently we only support one policy per namespace but
          // this will change in the future.
          if(policies.length > 0){
            const policy: NamespaceAutoPrunePolicy = policies[0];
            setMethod(policy.method);
            setUuid(policy.uuid);
            switch(policy.method){
              case AutoPruneMethod.TAG_NUMBER:
                setTagCount(policy.value as number);
                break;
              case AutoPruneMethod.TAG_CREATION_DATE:
                setTagAge(policy.value as string);
                break;
              default:
                // TODO: display error message that no method was selected
            }
          }
      }
    }, [successFetchingPolicies]);

    const onSave = (e) => {
      e.preventDefault();
      let value = null;
      switch(method){
        case AutoPruneMethod.TAG_NUMBER:
          value = tagCount;
          break;
        case AutoPruneMethod.TAG_CREATION_DATE:
          value = tagAge;
          break;
        case AutoPruneMethod.NONE:
          // Delete the policy is done by setting the method to none
          if(!isNullOrUndefined(uuid)){
            deletePolicy(uuid);
          }
          return;
        default:
          // TODO: display error message that no method was selected, probably will never reach here
      }
      if(isNullOrUndefined(uuid)){
        createPolicy({method: method, value: value});
      } else {
        updatePolicy({uuid: uuid, method: method, value: value})
      }
    }

    return (
    <Form id="autpruning-form" maxWidth="70%">
      <FormGroup
        isInline
        label="Prune Method"
        fieldId="method"
        helperText="The method used to prune tags."
      >
        <FormSelect
          placeholder=""
          aria-label="namespace-auto-prune-form"
          data-testid=""
          value={method}
          onChange={(val) => setMethod(val as AutoPruneMethod)}
        >
            <FormSelectOption
                key={1}
                value={AutoPruneMethod.NONE}
                label="None"
            />
            <FormSelectOption
                key={2}
                value={AutoPruneMethod.TAG_NUMBER}
                label="By number of tags"
            />
            <FormSelectOption
                key={3}
                value={AutoPruneMethod.TAG_CREATION_DATE}
                label="By age of tags"
            />
        </FormSelect>
      </FormGroup>
      <Conditional if={method===AutoPruneMethod.TAG_NUMBER}>
        <FormGroup
            isInline
            label="Prune by tag count."
            fieldId=""
            helperText=""
        >
            <NumberInput
                value={tagCount}
                onMinus={()=>{tagCount > 0 ? setTagCount(tagCount-1) : setTagCount(0)}}
                onChange={(e)=>{
                    // TODO: display error message to use that input is NaN
                    let val = Number((e.target as HTMLInputElement).value);
                    if(!isNaN(val)) {
                      setTagCount(val)
                    }
                }}
                onPlus={()=>{setTagCount(tagCount+1)}}
                inputAriaLabel="number of days"
                minusBtnAriaLabel="minus"
                plusBtnAriaLabel="plus"
            />
        </FormGroup>
      </Conditional>
      <Conditional if={method===AutoPruneMethod.TAG_CREATION_DATE}>
        <FormGroup
            isInline
            label="Prune tags older than X days."
            fieldId=""
            helperText=""
        >
          {/* TODO: validate this input that it's a valid date */}
          <TextInput value={tagAge} type="text" onChange={(value, _) => setTagAge(value)} aria-label="tag age text input" />
        </FormGroup>
      </Conditional>

      <ActionGroup>
        <Flex
          justifyContent={{default: 'justifyContentFlexEnd'}}
          width="100%"
        >
          <Button
            variant="primary"
            type="submit"
            onClick={onSave}
            isDisabled={false}
          >
            Save
          </Button>
        </Flex>
      </ActionGroup>
    </Form>
    )
}

interface AutoPruning {
    org: string;
}
