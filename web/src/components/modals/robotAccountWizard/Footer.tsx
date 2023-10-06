import {Button} from '@patternfly/react-core';
import {
  WizardContextConsumer,
  WizardFooter,
} from '@patternfly/react-core/deprecated';

export default function Footer(props: FooterProps) {
  if (props.isDrawerExpanded) {
    return null;
  }
  return (
    <WizardFooter>
      <WizardContextConsumer>
        {({activeStep, onNext, onBack, onClose}) => {
          return (
            <>
              {activeStep.name != 'Review and Finish' ? (
                <Button
                  data-testid="next-btn"
                  variant="primary"
                  type="submit"
                  onClick={onNext}
                >
                  Next
                </Button>
              ) : null}
              {activeStep.name != 'Robot name and description' ? (
                <Button variant="secondary" type="submit" onClick={onBack}>
                  Back
                </Button>
              ) : (
                ''
              )}
              {activeStep.name == 'Robot name and description' ||
              activeStep.name == 'Review and Finish' ? (
                <Button
                  data-testid="review-and-finish-btn"
                  isDisabled={!props.isDataValid()}
                  variant="secondary"
                  onClick={props.onSubmit}
                  id="create-robot-submit"
                >
                  Review and Finish
                </Button>
              ) : null}
              <Button variant="link" onClick={onClose} id="create-robot-cancel">
                Cancel
              </Button>
            </>
          );
        }}
      </WizardContextConsumer>
    </WizardFooter>
  );
}

interface FooterProps {
  onSubmit: () => void;
  isDrawerExpanded: boolean;
  isDataValid: () => boolean;
}
