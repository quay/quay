import React from 'react';
import {render, screen, fireEvent} from '@testing-library/react';
import {ArchitectureFilter} from '../ArchitectureFilter';

describe('ArchitectureFilter', () => {
  const mockOnChange = jest.fn();

  beforeEach(() => {
    mockOnChange.mockClear();
  });

  it('renders with no selection and shows "All architectures" placeholder', () => {
    render(
      <ArchitectureFilter selectedArchitectures={[]} onChange={mockOnChange} />,
    );

    expect(screen.getByText('All architectures')).toBeInTheDocument();
    expect(
      screen.getByText(
        'All architectures will be mirrored from multi-arch images.',
      ),
    ).toBeInTheDocument();
  });

  it('shows all 4 architecture options when opened', () => {
    render(
      <ArchitectureFilter selectedArchitectures={[]} onChange={mockOnChange} />,
    );

    // Open the dropdown
    fireEvent.click(screen.getByTestId('architecture-filter-toggle'));

    // Check all 4 options are present
    expect(screen.getByText('AMD64 (x86_64)')).toBeInTheDocument();
    expect(screen.getByText('ARM64 (aarch64)')).toBeInTheDocument();
    expect(screen.getByText('PowerPC 64 LE')).toBeInTheDocument();
    expect(screen.getByText('IBM Z (s390x)')).toBeInTheDocument();
  });

  it('allows selecting multiple architectures', () => {
    const {rerender} = render(
      <ArchitectureFilter selectedArchitectures={[]} onChange={mockOnChange} />,
    );

    // Open the dropdown
    fireEvent.click(screen.getByTestId('architecture-filter-toggle'));

    // Select amd64
    fireEvent.click(screen.getByTestId('architecture-option-amd64'));
    expect(mockOnChange).toHaveBeenCalledWith(['amd64']);

    // Rerender with amd64 selected
    rerender(
      <ArchitectureFilter
        selectedArchitectures={['amd64']}
        onChange={mockOnChange}
      />,
    );

    // Open the dropdown again
    fireEvent.click(screen.getByTestId('architecture-filter-toggle'));

    // Select arm64
    fireEvent.click(screen.getByTestId('architecture-option-arm64'));
    expect(mockOnChange).toHaveBeenCalledWith(['amd64', 'arm64']);
  });

  it('allows deselecting architectures', () => {
    render(
      <ArchitectureFilter
        selectedArchitectures={['amd64', 'arm64']}
        onChange={mockOnChange}
      />,
    );

    // Open the dropdown
    fireEvent.click(screen.getByTestId('architecture-filter-toggle'));

    // Deselect amd64
    fireEvent.click(screen.getByTestId('architecture-option-amd64'));
    expect(mockOnChange).toHaveBeenCalledWith(['arm64']);
  });

  it('clears all selections when "Clear all" is clicked', () => {
    render(
      <ArchitectureFilter
        selectedArchitectures={['amd64', 'arm64']}
        onChange={mockOnChange}
      />,
    );

    // Open the dropdown
    fireEvent.click(screen.getByTestId('architecture-filter-toggle'));

    // Click "Clear all"
    fireEvent.click(screen.getByTestId('architecture-clear-all'));
    expect(mockOnChange).toHaveBeenCalledWith([]);
  });

  it('is disabled when isDisabled is true', () => {
    render(
      <ArchitectureFilter
        selectedArchitectures={[]}
        onChange={mockOnChange}
        isDisabled={true}
      />,
    );

    const toggle = screen.getByTestId('architecture-filter-toggle');
    expect(toggle).toBeDisabled();
  });

  it('displays helper text for empty selection', () => {
    render(
      <ArchitectureFilter selectedArchitectures={[]} onChange={mockOnChange} />,
    );

    expect(screen.getByTestId('architecture-filter-helper')).toHaveTextContent(
      'All architectures will be mirrored from multi-arch images.',
    );
  });

  it('displays helper text with count for selection', () => {
    render(
      <ArchitectureFilter
        selectedArchitectures={['amd64', 'arm64']}
        onChange={mockOnChange}
      />,
    );

    expect(screen.getByTestId('architecture-filter-helper')).toHaveTextContent(
      'Only amd64, arm64 architecture(s) will be mirrored.',
    );
  });

  it('shows badge with selection count', () => {
    render(
      <ArchitectureFilter
        selectedArchitectures={['amd64', 'arm64', 'ppc64le']}
        onChange={mockOnChange}
      />,
    );

    expect(screen.getByTestId('architecture-filter-badge')).toHaveTextContent(
      '3',
    );
  });

  it('displays selected architectures in toggle', () => {
    render(
      <ArchitectureFilter
        selectedArchitectures={['amd64', 's390x']}
        onChange={mockOnChange}
      />,
    );

    const toggle = screen.getByTestId('architecture-filter-toggle');
    expect(toggle).toHaveTextContent('amd64, s390x');
  });

  it('does not show "Clear all" option when nothing is selected', () => {
    render(
      <ArchitectureFilter selectedArchitectures={[]} onChange={mockOnChange} />,
    );

    // Open the dropdown
    fireEvent.click(screen.getByTestId('architecture-filter-toggle'));

    // "Clear all" should not be visible
    expect(
      screen.queryByTestId('architecture-clear-all'),
    ).not.toBeInTheDocument();
  });
});
