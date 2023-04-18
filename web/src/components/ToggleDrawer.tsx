import {
  Drawer,
  DrawerPanelContent,
  DrawerContent,
  DrawerHead,
  DrawerActions,
  DrawerCloseButton,
  DrawerColorVariant,
} from '@patternfly/react-core';
import React from 'react';

export default function ToggleDrawer(props: ToggleDrawerProps) {
  const drawerRef = React.useRef<HTMLDivElement>();

  const onExpand = () => {
    drawerRef.current && drawerRef.current.focus();
  };

  const onCloseClick = () => {
    props.setIsExpanded(false);
  };

  const panelContent = (
    <DrawerPanelContent
      id="right-resize-panel"
      colorVariant={DrawerColorVariant.light200}
      className="drawer-styling "
    >
      <DrawerHead>
        <span tabIndex={props.isExpanded ? 0 : -1} ref={drawerRef}>
          {props.drawerpanelContent}
        </span>
        <DrawerActions>
          <DrawerCloseButton onClick={onCloseClick} />
        </DrawerActions>
      </DrawerHead>
    </DrawerPanelContent>
  );

  return (
    <>
      <Drawer
        isExpanded={props.isExpanded}
        onExpand={onExpand}
        position="right"
      >
        <DrawerContent
          colorVariant={DrawerColorVariant.default}
          panelContent={panelContent}
        ></DrawerContent>
      </Drawer>
    </>
  );
}

interface ToggleDrawerProps {
  isExpanded: boolean;
  setIsExpanded: (boolean) => void;
  drawerpanelContent: JSX.Element;
}
