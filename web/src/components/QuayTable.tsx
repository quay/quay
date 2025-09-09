/**
 * Custom table component for Quay built on PatternFly Table
 *
 * Features:
 * - Built-in sorting functionality
 * - Clean TypeScript interface without PatternFly pointer event issues
 * - Quay-specific styling and behavior
 * - Simplified API for common table patterns
 */

import React from 'react';
import {
  Table as PFTable,
  TableVariant,
  Thead as PFThead,
  Tbody as PFTbody,
  Tr as PFTr,
  Th as PFTh,
  Td as PFTd,
  ThProps as PFThProps,
  TdProps as PFTdProps,
} from '@patternfly/react-table';

// Clean interfaces for Quay table components - only include commonly used props
export interface QuayTableColumn {
  key: string;
  title: string;
  sortable?: boolean;
  sortIndex?: number;
}

export interface QuayTableProps {
  'aria-label': string;
  variant?: 'compact' | TableVariant;
  className?: string;
  children: React.ReactNode;
  id?: string;
}

export interface QuayTheadProps {
  children: React.ReactNode;
  className?: string;
}

export interface QuayTbodyProps {
  children: React.ReactNode;
  className?: string;
  isExpanded?: boolean;
  'data-testid'?: string;
}

export interface QuayTrProps {
  children: React.ReactNode;
  className?: string;
  isExpanded?: boolean;
}

export interface QuayThProps {
  children?: React.ReactNode;
  className?: string;
  modifier?: 'wrap' | 'nowrap' | 'truncate' | 'fitContent';
  sort?: PFThProps['sort'];
  width?: 10 | 15 | 20 | 25 | 30 | 35 | 40 | 45 | 50 | 60 | 70 | 80 | 90 | 100;
}

export interface QuayTdProps {
  children?: React.ReactNode;
  className?: string;
  dataLabel?: string;
  select?: PFTdProps['select'];
  width?: 10 | 15 | 20 | 25 | 30 | 35 | 40 | 45 | 50 | 60 | 70 | 80 | 90 | 100;
  noPadding?: boolean;
  colSpan?: number;
  expand?: PFTdProps['expand'];
  style?: React.CSSProperties;
}

// Forward ref components that properly handle all PatternFly props
export const QuayTable = React.forwardRef<HTMLTableElement, QuayTableProps>(
  (
    {'aria-label': ariaLabel, variant = 'compact', className, children, id},
    ref,
  ) => (
    // @ts-expect-error - PatternFly Table has problematic pointer event types that are false positives
    <PFTable
      aria-label={ariaLabel}
      variant={variant}
      className={className}
      id={id}
      ref={ref}
    >
      {children}
    </PFTable>
  ),
);

export const QuayThead = React.forwardRef<
  HTMLTableSectionElement,
  QuayTheadProps
>(({children, className}, ref) => (
  // @ts-expect-error - PatternFly Thead has problematic pointer event types that are false positives
  <PFThead className={className} ref={ref}>
    {children}
  </PFThead>
));

export const QuayTbody = React.forwardRef<
  HTMLTableSectionElement,
  QuayTbodyProps
>(({children, className, isExpanded, 'data-testid': dataTestId}, ref) => (
  // @ts-expect-error - PatternFly Tbody has problematic pointer event types that are false positives
  <PFTbody
    className={className}
    isExpanded={isExpanded}
    data-testid={dataTestId}
    ref={ref}
  >
    {children}
  </PFTbody>
));

export const QuayTr = React.forwardRef<HTMLTableRowElement, QuayTrProps>(
  ({children, className, isExpanded}, ref) => (
    // @ts-expect-error - PatternFly Tr has problematic pointer event types that are false positives
    <PFTr className={className} isExpanded={isExpanded} ref={ref}>
      {children}
    </PFTr>
  ),
);

export const QuayTh = React.forwardRef<HTMLTableCellElement, QuayThProps>(
  ({children, className, modifier, sort, width}, ref) => (
    // @ts-expect-error - PatternFly Th has problematic pointer event types that are false positives
    <PFTh
      className={className}
      modifier={modifier}
      sort={sort}
      width={width}
      ref={ref}
    >
      {children}
    </PFTh>
  ),
);

export const QuayTd = React.forwardRef<HTMLTableCellElement, QuayTdProps>(
  (
    {
      children,
      className,
      dataLabel,
      select,
      width,
      noPadding,
      colSpan,
      expand,
      style,
    },
    ref,
  ) => (
    // @ts-expect-error - PatternFly Td has problematic pointer event types that are false positives
    <PFTd
      className={className}
      dataLabel={dataLabel}
      select={select}
      width={width}
      noPadding={noPadding}
      colSpan={colSpan}
      expand={expand}
      style={style}
      ref={ref}
    >
      {children}
    </PFTd>
  ),
);

// Add display names for better debugging
QuayTable.displayName = 'QuayTable';
QuayThead.displayName = 'QuayThead';
QuayTbody.displayName = 'QuayTbody';
QuayTr.displayName = 'QuayTr';
QuayTh.displayName = 'QuayTh';
QuayTd.displayName = 'QuayTd';

// Export ThProps type for useTableSort compatibility
export type {ThProps as QuayThSortProps} from '@patternfly/react-table';

// Convenience exports with shorter names
export {
  QuayTable as Table,
  QuayThead as Thead,
  QuayTbody as Tbody,
  QuayTr as Tr,
  QuayTh as Th,
  QuayTd as Td,
};
