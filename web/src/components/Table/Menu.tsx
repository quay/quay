import {
  Menu as PFMenu,
  MenuList,
  MenuToggle,
  Popper,
} from '@patternfly/react-core';
import React, {useEffect, useRef} from 'react';

export default function Menu({isOpen, setIsOpen, ...props}: MenuProps) {
  const menuRef = useRef<HTMLDivElement>(null);
  const toggleRef = useRef<HTMLButtonElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const onToggleClick = (ev: React.MouseEvent) => {
    ev.stopPropagation(); // Stop handleClickOutside from handling
    setTimeout(() => {
      if (menuRef.current) {
        const firstElement = menuRef.current.querySelector(
          'li > button:not(:disabled), li > a:not(:disabled)',
        );
        firstElement && (firstElement as HTMLElement).focus();
      }
    }, 0);
    setIsOpen(!isOpen);
  };

  const handleMenuKeys = (event: KeyboardEvent) => {
    if (!isOpen) {
      return;
    }
    if (
      menuRef.current?.contains(event.target as Node) ||
      toggleRef.current?.contains(event.target as Node)
    ) {
      if (event.key === 'Escape' || event.key === 'Tab') {
        setIsOpen(!isOpen);
        toggleRef.current?.focus();
      }
    }
  };

  const handleClickOutside = (event: MouseEvent) => {
    if (isOpen && !menuRef.current?.contains(event.target as Node)) {
      setIsOpen(false);
    }
  };

  useEffect(() => {
    window.addEventListener('keydown', handleMenuKeys);
    window.addEventListener('click', handleClickOutside);
    return () => {
      window.removeEventListener('keydown', handleMenuKeys);
      window.removeEventListener('click', handleClickOutside);
    };
  }, [isOpen, menuRef]);

  return (
    <div ref={containerRef}>
      <Popper
        trigger={
          <MenuToggle onClick={onToggleClick} isExpanded={isOpen}>
            {props.toggle}
          </MenuToggle>
        }
        popper={
          <PFMenu ref={menuRef} containsFlyout>
            <MenuList>{props.items}</MenuList>
          </PFMenu>
        }
        appendTo={containerRef.current || undefined}
        isVisible={isOpen}
      />
    </div>
  );
}

interface MenuProps {
  items: React.ReactNode[];
  toggle: string;
  isOpen: boolean;
  setIsOpen: (isOpen: boolean) => void;
}
