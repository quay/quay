import {
  Button,
  useWizardContext,
  WizardFooterWrapper,
} from '@patternfly/react-core';

export default function Footer(props: FooterProps) {
  const {activeStep, goToNextStep, goToPrevStep, close} = useWizardContext();

  if (props.isDrawerExpanded) {
    return null;
  }

  return (
    <WizardFooterWrapper>
      {activeStep.name !== 'Review and Finish' && (
        <Button
          data-testid="next-btn"
          variant="primary"
          type="submit"
          onClick={goToNextStep}
        >
          Next
        </Button>
      )}

      {activeStep.name !== 'Robot name and description' && (
        <Button
          variant="secondary"
          type="submit"
          onClick={goToPrevStep}
          isDisabled={activeStep.index === 1}
        >
          Back
        </Button>
      )}

      {(activeStep.name === 'Robot name and description' ||
        activeStep.name === 'Review and Finish') && (
        <Button
          data-testid="review-and-finish-btn"
          isDisabled={!props.isDataValid()}
          variant="secondary"
          onClick={props.onSubmit}
          id="create-robot-submit"
        >
          Review and Finish
        </Button>
      )}

      <Button variant="link" onClick={close} id="create-robot-cancel">
        Cancel
      </Button>
    </WizardFooterWrapper>
  );
}

interface FooterProps {
  onSubmit: () => void;
  isDrawerExpanded: boolean;
  isDataValid: () => boolean;
}
