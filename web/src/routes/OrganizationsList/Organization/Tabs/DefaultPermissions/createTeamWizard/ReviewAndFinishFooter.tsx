import {
  Button,
  useWizardContext,
  WizardFooterWrapper,
} from '@patternfly/react-core';

export default function ReviewAndFinishFooter(
  props: ReviewAndFinishFooterProps,
) {
  const {activeStep, goToNextStep, goToPrevStep, close} = useWizardContext();

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

      {activeStep.name !== 'Name & Description' && (
        <Button
          variant="secondary"
          type="submit"
          onClick={goToPrevStep}
          isDisabled={activeStep.index === 1}
        >
          Back
        </Button>
      )}

      {(activeStep.name === 'Add team member (optional)' ||
        activeStep.name === 'Review and Finish') && (
        <Button
          data-testid="review-and-finish-wizard-btn"
          isDisabled={!props.canSubmit}
          variant="secondary"
          onClick={props.onSubmit}
          id="create-team-submit"
        >
          Review and Finish
        </Button>
      )}

      <Button variant="link" onClick={close} id="create-team-cancel">
        Cancel
      </Button>
    </WizardFooterWrapper>
  );
}

interface ReviewAndFinishFooterProps {
  onSubmit: () => void;
  canSubmit: boolean;
}
