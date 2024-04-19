import React, {useState} from 'react';
import {Button, Flex, FlexItem} from '@patternfly/react-core';
import {CodeEditor, Language} from '@patternfly/react-code-editor';

interface DescriptionEditorProps {
  description: string;
  onSave: (description: string) => void;
  onCancel: () => void;
}

export function DescriptionEditor(props: DescriptionEditorProps) {
  const [description, setDescription] = useState(props.description);
  const onEditorDidMount = (editor, monaco) => {
    editor.layout();
    editor.focus();
    monaco.editor.getModels()[0].updateOptions({tabSize: 5});
  };

  const onChange = (value) => {
    // eslint-disable-next-line no-console
    setDescription(value);
  };

  return (
    <Flex direction={{default: 'column'}}>
      <FlexItem>
        <CodeEditor
          code={description}
          isDarkTheme={true}
          isLineNumbersVisible={false}
          onChange={onChange}
          language={Language.markdown}
          onEditorDidMount={onEditorDidMount}
          height="500px"
        />
      </FlexItem>
      <FlexItem>
        <Flex>
          <FlexItem>
            <Button variant="primary" onClick={() => props.onSave(description)}>
              Save
            </Button>
          </FlexItem>
          <FlexItem>
            <Button variant="secondary" onClick={props.onCancel}>
              Cancel
            </Button>
          </FlexItem>
        </Flex>
      </FlexItem>
    </Flex>
  );
}
