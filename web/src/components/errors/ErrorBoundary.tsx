import React from 'react';

// Function getDerivedStateFromError required for Error Boundaries
// are only available on class components
class ErrorBoundary extends React.Component<
  ErrorBoundryProps,
  ErrorBoundryState
> {
  constructor(props: ErrorBoundryProps) {
    super(props);
    this.state = {
      hasError: props.hasError,
      fallback: props.fallback,
    };
  }

  // Capture the error that occured when rendering child component
  static getDerivedStateFromError(error) {
    console.error(error);
    return {hasError: true};
  }

  render() {
    if (this.state.hasError || this.props.hasError) {
      return <>{this.props.fallback}</>;
    }
    return <>{this.props.children}</>;
  }
}

interface ErrorBoundryState {
  hasError: boolean;
  fallback: React.ReactNode;
  children?: React.ReactNode;
}

interface ErrorBoundryProps {
  fallback: React.ReactNode;
  hasError?: boolean;
  children?: React.ReactNode;
}

export default ErrorBoundary;
