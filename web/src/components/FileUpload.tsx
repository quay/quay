import {FileUpload as PFFileUpload, DropEvent} from '@patternfly/react-core';
import {ChangeEvent, useState} from 'react';
import {isNullOrUndefined} from 'src/libs/utils';

export default function FileUpload(props: FileUploadProps) {
  const [filename, setFilename] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const handleFileInputChange = (_, file: File) => {
    setFilename(file.name);
  };

  const handleDataChange = (_event: DropEvent, value: string) => {
    props.onValueChange(value);
  };

  const handleClear = () => {
    setFilename('');
    props.onValueChange('');
    if (!isNullOrUndefined(props.onClear)) {
      props.onClear();
    }
  };

  const handleFileReadStarted = (_event: DropEvent, _fileHandle: File) => {
    setIsLoading(true);
  };

  const handleFileReadFinished = (_event: DropEvent, _fileHandle: File) => {
    setIsLoading(false);
  };

  return (
    <PFFileUpload
      id={isNullOrUndefined(props.id) ? 'upload-file' : props.id}
      type="text"
      value={props.value}
      filename={filename}
      filenamePlaceholder="Drag and drop a file or upload one"
      onFileInputChange={handleFileInputChange}
      onDataChange={handleDataChange}
      onReadStarted={handleFileReadStarted}
      onReadFinished={handleFileReadFinished}
      onClearClick={handleClear}
      isLoading={isLoading}
      allowEditingUploadedText={false}
      browseButtonText="Upload"
    />
  );
}

interface FileUploadProps {
  id?: string;
  value: string | File;
  onValueChange: (value: string | File) => void;
  onClear?: () => void;
}
