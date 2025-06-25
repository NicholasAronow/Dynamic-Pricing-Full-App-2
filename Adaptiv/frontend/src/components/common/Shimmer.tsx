import React from 'react';
import styled, { keyframes } from 'styled-components';

// Types for our Shimmer component
export interface ShimmerProps {
  width?: string | number;
  height?: string | number;
  borderRadius?: string | number;
  className?: string;
  margin?: string;
  style?: React.CSSProperties;
  isText?: boolean;
  isCircle?: boolean;
  inline?: boolean;
}

// Shimmer animation keyframe
const shimmerAnimation = keyframes`
  0% {
    background-position: -468px 0;
  }
  100% {
    background-position: 468px 0;
  }
`;

// Styled component for the shimmer effect
const ShimmerContainer = styled.div<ShimmerProps>`
  display: ${props => props.inline ? 'inline-block' : 'block'};
  width: ${props => props.isText ? '100%' : typeof props.width === 'number' ? `${props.width}px` : props.width || '100%'};
  height: ${props => typeof props.height === 'number' ? `${props.height}px` : props.height || '20px'};
  margin: ${props => props.margin || '0'};
  border-radius: ${props => 
    props.isCircle 
      ? '50%' 
      : typeof props.borderRadius === 'number' 
        ? `${props.borderRadius}px` 
        : props.borderRadius || '4px'
  };
  background: linear-gradient(to right, #f6f7f8 8%, #edeef1 38%, #f6f7f8 54%);
  background-size: 1000px 640px;
  position: relative;
  overflow: hidden;
  animation: ${shimmerAnimation} 1.5s linear infinite;
`;

// Text shimmer specific styling
const TextLine = styled(ShimmerContainer)<{ last?: boolean }>`
  margin-bottom: ${props => props.last ? '0' : '10px'};
  width: ${props => props.width || '100%'};
`;

// ShimmerText component for text placeholders with multiple lines
export const ShimmerText: React.FC<{
  lines?: number;
  lineHeight?: number | string;
  width?: (string | number)[];
  className?: string;
}> = ({ lines = 3, lineHeight = 15, width = ['100%', '90%', '80%'], className }) => {
  return (
    <div className={className}>
      {Array.from({ length: lines }).map((_, i) => (
        <TextLine
          key={i}
          height={lineHeight}
          width={Array.isArray(width) ? width[i % width.length] : width}
          last={i === lines - 1}
          isText
        />
      ))}
    </div>
  );
};

// Main Shimmer component
const Shimmer: React.FC<ShimmerProps> = (props) => {
  return <ShimmerContainer {...props} />;
};

export default Shimmer;
