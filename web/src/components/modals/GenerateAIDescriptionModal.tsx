import {
  Alert,
  Button,
  FormGroup,
  FormSelect,
  FormSelectOption,
  Modal,
  ModalVariant,
  Spinner,
  TextArea,
  TextContent,
  Text,
  TextVariants,
  Checkbox,
} from '@patternfly/react-core';
import {useState, useEffect} from 'react';
import {
  useAIDescriptionTags,
  useGenerateAIDescription,
  useAISettings,
} from 'src/hooks/UseAIDescription';
import {MagicIcon} from '@patternfly/react-icons';

interface GenerateAIDescriptionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onApply: (description: string) => void;
  organization: string;
  repository: string;
}

export default function GenerateAIDescriptionModal({
  isOpen,
  onClose,
  onApply,
  organization,
  repository,
}: GenerateAIDescriptionModalProps) {
  const [selectedTag, setSelectedTag] = useState<string>('');
  const [generatedDescription, setGeneratedDescription] = useState<string>('');
  const [forceRegenerate, setForceRegenerate] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [hasGenerated, setHasGenerated] = useState<boolean>(false);

  // Check if AI is enabled for this org
  const {data: aiSettings, isLoading: isLoadingSettings} = useAISettings(
    organization,
    isOpen,
  );

  // Fetch available tags
  const {data: tagsData, isLoading: isLoadingTags} = useAIDescriptionTags(
    organization,
    repository,
    isOpen,
  );

  // Generate description mutation
  const generateMutation = useGenerateAIDescription({
    onSuccess: (data) => {
      setGeneratedDescription(data.description);
      setHasGenerated(true);
      setError(null);
    },
    onError: (err) => {
      setError(err.message || 'Failed to generate description');
    },
  });

  // Set default tag when tags load
  useEffect(() => {
    if (tagsData?.tags && tagsData.tags.length > 0 && !selectedTag) {
      // Try to find 'latest' tag, otherwise use first tag
      const latestTag = tagsData.tags.find((t) => t.name === 'latest');
      setSelectedTag(latestTag?.name || tagsData.tags[0].name);
    }
  }, [tagsData, selectedTag]);

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setGeneratedDescription('');
      setError(null);
      setHasGenerated(false);
      setForceRegenerate(false);
    }
  }, [isOpen]);

  const handleGenerate = () => {
    if (!selectedTag) {
      setError('Please select a tag');
      return;
    }
    setError(null);
    generateMutation.mutate({
      namespace: organization,
      repository: repository,
      request: {
        tag: selectedTag,
        force_regenerate: forceRegenerate,
      },
    });
  };

  const handleApply = () => {
    onApply(generatedDescription);
    onClose();
  };

  const handleDescriptionChange = (value: string) => {
    setGeneratedDescription(value);
  };

  const isLoading = isLoadingSettings || isLoadingTags;
  const isGenerating = generateMutation.isLoading;
  const aiEnabled =
    aiSettings?.description_generator_enabled &&
    aiSettings?.credentials_verified;

  // Check if AI is not configured
  const needsConfiguration =
    aiSettings &&
    (!aiSettings.credentials_configured || !aiSettings.credentials_verified);

  return (
    <Modal
      variant={ModalVariant.medium}
      title="Generate Description with AI"
      titleIconVariant={MagicIcon}
      isOpen={isOpen}
      onClose={onClose}
      actions={
        hasGenerated
          ? [
              <Button
                key="apply"
                variant="primary"
                onClick={handleApply}
                isDisabled={!generatedDescription}
              >
                Apply Description
              </Button>,
              <Button
                key="regenerate"
                variant="secondary"
                onClick={handleGenerate}
                isLoading={isGenerating}
                isDisabled={isGenerating}
              >
                Regenerate
              </Button>,
              <Button key="cancel" variant="link" onClick={onClose}>
                Cancel
              </Button>,
            ]
          : [
              <Button
                key="generate"
                variant="primary"
                onClick={handleGenerate}
                isLoading={isGenerating}
                isDisabled={
                  isLoading || isGenerating || !aiEnabled || !selectedTag
                }
              >
                Generate
              </Button>,
              <Button key="cancel" variant="link" onClick={onClose}>
                Cancel
              </Button>,
            ]
      }
    >
      {isLoading && (
        <div style={{textAlign: 'center', padding: '2rem'}}>
          <Spinner size="lg" />
          <TextContent>
            <Text component={TextVariants.small}>Loading...</Text>
          </TextContent>
        </div>
      )}

      {!isLoading && needsConfiguration && (
        <Alert
          variant="warning"
          isInline
          title="AI not configured"
          style={{marginBottom: '1rem'}}
        >
          AI description generation is not configured for this organization.
          Please configure AI settings in the organization settings.
        </Alert>
      )}

      {!isLoading &&
        !needsConfiguration &&
        !aiSettings?.description_generator_enabled && (
          <Alert
            variant="info"
            isInline
            title="AI disabled"
            style={{marginBottom: '1rem'}}
          >
            AI description generation is disabled for this organization. Enable
            it in organization settings.
          </Alert>
        )}

      {error && (
        <Alert
          variant="danger"
          isInline
          title="Error"
          style={{marginBottom: '1rem'}}
        >
          {error}
        </Alert>
      )}

      {!isLoading && aiEnabled && !hasGenerated && (
        <>
          <TextContent style={{marginBottom: '1rem'}}>
            <Text component={TextVariants.p}>
              Generate a description for this repository using AI. The
              description will be generated based on the container image layer
              history and configuration.
            </Text>
          </TextContent>

          <FormGroup label="Select Tag" isRequired fieldId="tag-select">
            <FormSelect
              id="tag-select"
              value={selectedTag}
              onChange={(_event, value) => setSelectedTag(value)}
              aria-label="Select tag"
            >
              {tagsData?.tags?.map((tag) => (
                <FormSelectOption
                  key={tag.name}
                  value={tag.name}
                  label={tag.name}
                />
              ))}
            </FormSelect>
          </FormGroup>

          <FormGroup fieldId="force-regenerate" style={{marginTop: '1rem'}}>
            <Checkbox
              id="force-regenerate"
              label="Force regenerate (bypass cache)"
              isChecked={forceRegenerate}
              onChange={(_event, checked) => setForceRegenerate(checked)}
            />
          </FormGroup>
        </>
      )}

      {!isLoading && hasGenerated && (
        <>
          <TextContent style={{marginBottom: '1rem'}}>
            <Text component={TextVariants.p}>
              Review and edit the generated description below. Click &quot;Apply
              Description&quot; to use it.
            </Text>
            {generateMutation.data?.cached && (
              <Text component={TextVariants.small}>
                <em>This description was retrieved from cache.</em>
              </Text>
            )}
          </TextContent>

          <FormGroup
            label="Generated Description"
            fieldId="generated-description"
          >
            <TextArea
              id="generated-description"
              value={generatedDescription}
              onChange={(_event, value) => handleDescriptionChange(value)}
              rows={12}
              aria-label="Generated description"
            />
          </FormGroup>

          <TextContent style={{marginTop: '0.5rem'}}>
            <Text component={TextVariants.small}>
              You can edit the description before applying it. Supports Markdown
              formatting.
            </Text>
          </TextContent>
        </>
      )}
    </Modal>
  );
}
