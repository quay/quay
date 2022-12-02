import {
  Button,
  WizardContextConsumer,
  WizardFooter,
} from '@patternfly/react-core';

export default function ReviewAndFinishFooter(
  props: ReviewAndFinishFooterProps,
) {
  return (
    <WizardFooter>
      <WizardContextConsumer>
        {({
          activeStep,
          goToStepByName,
          goToStepById,
          onNext,
          onBack,
          onClose,
        }) => {
          return (
            <>
              {activeStep.name !== 'Review and Finish' ? (
                <Button
                  data-testid="next-btn"
                  variant="primary"
                  type="submit"
                  onClick={onNext}
                >
                  Next
                </Button>
              ) : null}
              {activeStep.name !== 'Name & Description' ? (
                <Button variant="secondary" type="submit" onClick={onBack}>
                  Back
                </Button>
              ) : null}
              {activeStep.name === 'Add team member (optional)' ||
              activeStep.name === 'Review and Finish' ? (
                <Button
                  data-testid="review-and-finish-wizard-btn"
                  isDisabled={!props.canSubmit}
                  variant="secondary"
                  onClick={props.onSubmit}
                  id="create-team-submit"
                >
                  Review and Finish
                </Button>
              ) : null}
              <Button variant="link" onClick={onClose} id="create-team-cancel">
                Cancel
              </Button>
            </>
          );
        }}
      </WizardContextConsumer>
    </WizardFooter>
  );
}

interface ReviewAndFinishFooterProps {
  onSubmit: () => void;
  canSubmit: boolean;
}
