import React from 'react';
import {IAvatar} from 'src/resources/OrganizationResource';

type AvatarSize = 'sm' | 'md' | 'lg' | 'xl';

interface AvatarProps {
  avatar: IAvatar;
  size?: AvatarSize;
  className?: string;
  'data-testid'?: string;
}

export default function Avatar({
  avatar,
  size = 'md',
  className = '',
  'data-testid': dataTestId,
}: AvatarProps) {
  const firstLetter = avatar.name ? avatar.name.charAt(0).toUpperCase() : '?';

  // PatternFly 5 Avatar sizing standards
  const sizeMap: Record<
    AvatarSize,
    {width: string; height: string; fontSize: string}
  > = {
    sm: {width: '1.5rem', height: '1.5rem', fontSize: '0.625rem'}, // 24px, 10px font
    md: {width: '2.25rem', height: '2.25rem', fontSize: '0.875rem'}, // 36px, 14px font
    lg: {width: '4.5rem', height: '4.5rem', fontSize: '1.75rem'}, // 72px, 28px font
    xl: {width: '8rem', height: '8rem', fontSize: '3.125rem'}, // 128px, 50px font
  };

  const dimensions = sizeMap[size];

  const avatarStyle: React.CSSProperties = {
    width: dimensions.width,
    height: dimensions.height,
    backgroundColor: avatar.color,
    color: 'white',
    borderRadius: '30em', // PatternFly's border radius for circular avatars
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: dimensions.fontSize,
    fontWeight: 'bold',
    flexShrink: 0,
    border: '0px solid transparent', // Match PatternFly default border
  };

  return (
    <div
      className={`pf-v5-c-avatar ${className}`}
      style={avatarStyle}
      title={`${avatar.name} avatar`}
      aria-label={`${avatar.name} avatar`}
      data-testid={dataTestId}
    >
      {firstLetter}
    </div>
  );
}
