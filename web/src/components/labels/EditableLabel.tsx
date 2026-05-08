import {Label, TextInput} from '@patternfly/react-core';
import {useEffect, useRef, useState} from 'react';

export default function EditableLabel(props: EditableLabelProps) {
  const [isEditable, setIsEditable] = useState(false);
  const wrapperRef = useRef(null);
  const valueRef = useRef(props.value);
  valueRef.current = props.value;

  useEffect(() => {
    function handleClickOutside(event) {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target)) {
        setIsEditable(false);
        props.onEditComplete(valueRef.current);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [wrapperRef, props.onEditComplete]);

  if (isEditable) {
    return (
      <TextInput
        id="new-label-input"
        ref={wrapperRef}
        value={props.value}
        onChange={(_event, newValue) => props.setValue(newValue.trim())}
        style={{width: '50%'}}
        placeholder="key=value"
        validated={props.invalid ? 'error' : 'default'}
      />
    );
  } else {
    return (
      <Label
        color={props.invalid ? 'red' : 'blue'}
        key="add-label"
        className="label"
        onClick={() => {
          setIsEditable(true);
        }}
        style={{textDecorationStyle: 'dotted'}}
      >
        {props.value === '' ? 'Add new label' : props.value}
      </Label>
    );
  }
}

interface EditableLabelProps {
  invalid?: boolean;
  value: string;
  setValue: (value: string) => void;
  onEditComplete: (value: string) => void;
}
