import React from 'react';
import styled from 'styled-components';
import { Card, Row, Col } from 'antd';
import Shimmer, { ShimmerText } from './Shimmer';

// Base styles
const cardBodyPadding = '24px';

// Styled components for various shimmer loaders
const ShimmerCardWrapper = styled(Card)`
  overflow: hidden;
  margin-bottom: 24px;
  height: 100%;
`;

const ShimmerHeaderSection = styled.div`
  margin-bottom: 16px;
`;

const FlexRow = styled.div`
  display: flex;
  align-items: center;
  margin-bottom: 16px;
  justify-content: space-between;
`;

const StatisticWrapper = styled.div`
  margin-bottom: 16px;
  width: 100%;
`;

const ChartContainer = styled.div`
  height: 300px;
  display: flex;
  flex-direction: column;
`;

const LegendContainer = styled.div`
  display: flex;
  justify-content: center;
  margin-top: 12px;
  gap: 16px;
`;

const LegendItem = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
`;

const TableContainer = styled.div`
  width: 100%;
`;

const TableHeader = styled.div`
  display: flex;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid #f0f0f0;
`;

const TableRow = styled.div`
  display: flex;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid #f0f0f0;
`;

// Shimmer Loaders Components
export const ShimmerCardHeader: React.FC = () => (
  <ShimmerHeaderSection>
    <Shimmer height={28} width="60%" margin="0 0 8px 0" />
    <Shimmer height={16} width="40%" />
  </ShimmerHeaderSection>
);

export const ShimmerStatistic: React.FC = () => (
  <StatisticWrapper>
    <Shimmer height={16} width="40%" margin="0 0 8px 0" />
    <Shimmer height={24} width="60%" margin="0 0 4px 0" />
  </StatisticWrapper>
);

export const ShimmerCard: React.FC<{
  title?: boolean;
  height?: string | number;
}> = ({ title = true, height = 'auto' }) => (
  <ShimmerCardWrapper bodyStyle={{ padding: cardBodyPadding, height }}>
    {title && <ShimmerCardHeader />}
    <ShimmerText lines={3} />
  </ShimmerCardWrapper>
);

export const ShimmerChart: React.FC<{
  height?: string | number;
}> = ({ height = 300 }) => (
  <Card bodyStyle={{ padding: cardBodyPadding }}>
    <ShimmerCardHeader />
    <ChartContainer style={{ height }}>
      <Shimmer height="100%" />
      <LegendContainer>
        {[1, 2, 3].map((i) => (
          <LegendItem key={i}>
            <Shimmer width={16} height={16} borderRadius={4} inline />
            <Shimmer width={60} height={14} inline />
          </LegendItem>
        ))}
      </LegendContainer>
    </ChartContainer>
  </Card>
);

// Specific shimmer for area charts with smooth curves
export const ShimmerBarChart: React.FC<{
  height?: string | number;
  title?: React.ReactNode;
  showTimeFrameSelector?: boolean;
}> = ({ height = 300, title, showTimeFrameSelector = false }) => {
  // Chart container styles
  const AreaChartContainer = styled.div`
    position: relative;
    height: calc(100% - 40px);
    padding-bottom: 40px; /* Space for x-axis */
    z-index: 2;
  `;
  
  const AxisLine = styled.div`
    position: absolute;
    background-color: #f0f0f0;
  `;

  const XAxis = styled(AxisLine)`
    bottom: 0;
    left: 0;
    width: 100%;
    height: 1px;
    z-index: 0;
  `;

  const YAxis = styled(AxisLine)`
    top: 0;
    left: 0;
    width: 1px;
    height: 100%;
    z-index: 0;
  `;
  
  const YAxisLabels = styled.div`
    position: absolute;
    left: -50px;
    top: 0;
    height: 100%;
    width: 40px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding-bottom: 40px;
  `;
  
  const XAxisLabels = styled.div`
    position: absolute;
    bottom: 0;
    left: 0;
    width: 100%;
    height: 30px;
    display: flex;
    justify-content: space-between;
  `;

  // Area chart with gradient and shimmer effect
  const ShimmerAnimation = styled.div`
    @keyframes shimmer {
      0% { background-position: -1000px 0; }
      100% { background-position: 1000px 0; }
    }
    position: absolute;
    height: 100%;
    width: 100%;
    background: linear-gradient(to right, rgba(232, 234, 237, 0.2) 8%, rgba(240, 240, 240, 0.5) 18%, rgba(232, 234, 237, 0.2) 33%);
    background-size: 2000px 100%;
    animation: shimmer 1.5s infinite linear;
  `;

  // Area chart with gradient
  const AreaChart = styled.div`
    position: absolute;
    bottom: 40px;
    left: 0;
    width: 100%;
    height: calc(100% - 40px);
    background: linear-gradient(to bottom, rgba(200, 200, 200, 0.8) 0%, rgba(232, 234, 237, 0.1) 100%);
    clip-path: polygon(
      0% 100%, /* bottom left */
      0% 65%, /* left side start */
      1% 64.5%,
      2% 64%,
      3% 63.5%,
      4% 63%,
      5% 62.5%,
      6% 62%,
      7% 61%,
      8% 60.5%,
      9% 60%,
      10% 60%,
      11% 61%,
      12% 62%,
      13% 64%,
      14% 66%,
      15% 68%,
      16% 70%,
      17% 72%,
      18% 74%,
      19% 75%,
      20% 76%,
      21% 75%,
      22% 74%,
      23% 71%,
      24% 68%,
      25% 64%,
      26% 60%,
      27% 56%,
      28% 52%,
      29% 48%,
      30% 44%,
      31% 42%,
      32% 41%,
      33% 42%,
      34% 43%,
      35% 44%,
      36% 45%,
      37% 46%,
      38% 47%,
      39% 47.5%,
      40% 48%,
      41% 47.5%,
      42% 47%,
      43% 45.5%,
      44% 44%,
      45% 42%,
      46% 40%,
      47% 38%,
      48% 36%,
      49% 34%,
      50% 32%,
      51% 31.5%,
      52% 31%,
      53% 32%,
      54% 33%,
      55% 34%,
      56% 35%,
      57% 36%,
      58% 37%,
      59% 38%,
      60% 39%,
      61% 40.5%,
      62% 42%,
      63% 44%,
      64% 46%,
      65% 48%,
      66% 50%,
      67% 52%,
      68% 54%,
      69% 55%,
      70% 56%,
      71% 55%,
      72% 54%,
      73% 51%,
      74% 48%,
      75% 44%,
      76% 40%,
      77% 36%,
      78% 32%,
      79% 28%,
      80% 24%,
      81% 23%,
      82% 22%,
      83% 22%,
      84% 23%,
      85% 24%,
      86% 25%,
      87% 26%,
      88% 27%,
      89% 28%,
      90% 29%,
      91% 30%,
      92% 30.5%,
      93% 31%,
      94% 31.5%,
      95% 32%,
      96% 32.5%,
      97% 33%,
      98% 33.5%,
      99% 34%,
      100% 34.5%, /* right side end */
      100% 100% /* bottom right */
    );
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    overflow: hidden; /* Important to contain the shimmer effect */
  `;

  // Line on top of area
  const AreaLine = styled.div`
    position: absolute;
    width: 100%;
    height: 2px;
    background: #c0c0c0;
    transform: translateY(-1px);
    opacity: 0.8;
  `;

  return (
    <Card 
      title={
        title ? (
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            {title}
            {showTimeFrameSelector && (
              <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                {[1, 2, 3, 4, 5].map((i) => (
                  <Shimmer 
                    key={`btn-${i}`}
                    width={30} 
                    height={24} 
                    margin="0 4px"
                    borderRadius={2}
                    inline
                  />
                ))}
              </div>
            )}
          </div>
        ) : (
          <ShimmerCardHeader />
        )
      }
      bodyStyle={{ padding: cardBodyPadding }}
    >
      <ChartContainer style={{ height, position: 'relative', paddingLeft: 50, overflow: 'visible' }}>
        <AreaChartContainer>
          <XAxis />
          {/* Y-axis labels */}
          <YAxisLabels>
            {[1, 2, 3, 4].map((i) => (
              <Shimmer 
                key={`y-${i}`} 
                width={30} 
                height={14}
              />
            ))}
          </YAxisLabels>
          
          {/* Area chart */}
          <AreaChart>
            {/* Add the shimmer animation inside the chart */}
            <ShimmerAnimation />
          </AreaChart>
          
          {/* X-axis labels */}
          <XAxisLabels>
            {Array.from({ length: 5 }).map((_, i) => (
              <Shimmer 
                key={`x-${i}`} 
                width={40} 
                height={14}
              />
            ))}
          </XAxisLabels>
        </AreaChartContainer>
        
        <LegendContainer style={{ marginTop: 20 }}>
          <LegendItem>
            <Shimmer width={16} height={16} borderRadius={4} inline />
            <Shimmer width={60} height={14} inline />
          </LegendItem>
          <LegendItem>
            <Shimmer width={16} height={16} borderRadius={4} style={{ backgroundColor: '#00C853' }} inline />
            <Shimmer width={60} height={14} inline />
          </LegendItem>
        </LegendContainer>
      </ChartContainer>
    </Card>
  );
};

export const ShimmerTable: React.FC<{
  rows?: number;
  columns?: number;
}> = ({ rows = 5, columns = 4 }) => (
  <Card bodyStyle={{ padding: cardBodyPadding }}>
    <ShimmerCardHeader />
    <TableContainer>
      <TableHeader>
        {Array.from({ length: columns }).map((_, i) => (
          <Shimmer 
            key={`header-${i}`}
            width={`${100 / columns - 2}%`}
            height={16}
          />
        ))}
      </TableHeader>
      {Array.from({ length: rows }).map((_, rowIdx) => (
        <TableRow key={`row-${rowIdx}`}>
          {Array.from({ length: columns }).map((_, colIdx) => (
            <Shimmer 
              key={`cell-${rowIdx}-${colIdx}`}
              width={`${100 / columns - 2}%`}
              height={16}
            />
          ))}
        </TableRow>
      ))}
    </TableContainer>
  </Card>
);

export const ShimmerDashboardStats: React.FC = () => (
  <Row gutter={[16, 16]}>
    {[1, 2, 3, 4].map((i) => (
      <Col xs={24} sm={12} md={12} lg={6} key={i}>
        <Card>
          <FlexRow>
            <Shimmer width={40} height={40} isCircle />
            <ShimmerText lines={2} width={['60%', '40%']} />
          </FlexRow>
          <Shimmer height={24} width="70%" margin="0 0 8px 0" />
          <Shimmer height={16} width="40%" />
        </Card>
      </Col>
    ))}
  </Row>
);

export const ShimmerActionItems: React.FC = () => (
  <Card bodyStyle={{ padding: cardBodyPadding }}>
    <ShimmerCardHeader />
    {[1, 2, 3].map((i) => (
      <FlexRow key={i}>
        <Shimmer width={40} height={40} borderRadius={20} />
        <ShimmerText 
          lines={2} 
          width={['60%', '40%']}
        />
        <Shimmer width={60} height={32} borderRadius={4} />
      </FlexRow>
    ))}
  </Card>
);

export const ShimmerProductList: React.FC<{
  rows?: number;
}> = ({ rows = 5 }) => (
  <Card bodyStyle={{ padding: cardBodyPadding }}>
    <ShimmerCardHeader />
    {Array.from({ length: rows }).map((_, i) => (
      <FlexRow key={i}>
        <Shimmer width={40} height={40} style={{ marginRight: 16 }} />
        <div style={{ flex: 1 }}>
          <Shimmer height={18} width="70%" margin="0 0 8px 0" />
          <Shimmer height={14} width="50%" />
        </div>
        <div style={{ width: '20%', textAlign: 'right' }}>
          <Shimmer height={18} width="80%" margin="0 0 8px 0" />
          <Shimmer height={14} width="60%" />
        </div>
      </FlexRow>
    ))}
  </Card>
);

// Specialized shimmer for product performance (top/worst performers)
export const ShimmerProductPerformance: React.FC<{
  itemCount?: number;
  showTopAndBottom?: boolean;
}> = ({ itemCount = 3, showTopAndBottom = true }) => {
  // Product card shimmer
  const ProductPerformanceCard: React.FC = () => (
    <Card
      style={{ marginBottom: 8, borderRadius: 0, border: 'none' }}
      size="small"
      className="dashboard-card-item"
      bodyStyle={{ padding: '12px 24px' }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <Shimmer height={16} width="60%" margin="0 0 8px 0" />
            <Shimmer height={16} width={40} margin="0 0 8px 8px" borderRadius={12} />
          </div>
          <div style={{ marginTop: 4, display: 'flex', alignItems: 'center' }}>
            <Shimmer height={14} width={50} margin="4px 8px 0 0" />
            <Shimmer height={14} width={80} margin="4px 0 0 0" />
          </div>
        </div>
        <div style={{ textAlign: 'right', minWidth: '120px' }}>
          <div>
            <Shimmer height={16} width="80%" margin="0 0 8px 0" style={{ marginLeft: 'auto' }} />
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', marginTop: 4 }}>
            <Shimmer height={14} width="60%" />
          </div>
        </div>
      </div>
    </Card>
  );

  // Section title shimmer
  const SectionTitle: React.FC<{ color?: string }> = ({ color = '#3f8600' }) => (
    <div style={{ display: 'flex', alignItems: 'center', marginTop: 12, marginBottom: 16 }}>
      <Shimmer height={24} width={180} style={{ backgroundColor: color === '#3f8600' ? '#e6f5e6' : '#fce8e6' }} />
    </div>
  );

  return (
    <>
      {/* Top Performers */}
      <div>
        <SectionTitle color="#3f8600" />
        <div style={{ marginBottom: 36 }}>
          {Array.from({ length: itemCount }).map((_, index) => (
            <ProductPerformanceCard key={`top-${index}`} />
          ))}
        </div>
      </div>

      {/* Bottom Performers - only show if requested */}
      {showTopAndBottom && (
        <div>
          <SectionTitle color="#cf1322" />
          <div>
            {Array.from({ length: itemCount }).map((_, index) => (
              <ProductPerformanceCard key={`bottom-${index}`} />
            ))}
          </div>
        </div>
      )}
    </>
  );
};

// Example usage of combined shimmer loaders
// Specialized shimmer for the price recommendations page
export const ShimmerPriceRecommendations: React.FC = () => {
  // Column headers for price recommendations table
  const columns = [
    { title: 'Item' },
    { title: 'Current Price' },
    { title: 'Performance' },
    { title: 'Gross Margin' },
    { title: 'Net Margin' },
    { title: 'Recommendation' },
  ];

  return (
    <>
      {/* Summary statistics card */}
      <Card style={{ marginTop: 24, marginBottom: 24 }}>
        <Row gutter={24}>
          <Col span={8}>
            <div>
              <Shimmer height={14} width="60%" margin="8px 0 8px 0" />
              <Shimmer height={24} width="30%" />
              <Shimmer height={18} width="60%" margin="8px 0 8px 0" />
            </div>
          </Col>
          <Col span={8}>
            <div>
              <Shimmer height={14} width="40%" margin="8px 0 8px 0" />
              <Shimmer height={24} width="30%" />
            </div>
          </Col>
          <Col span={8}>
            <div>
              <Shimmer height={14} width="60%" margin="8px 0 8px 0" />
              <Shimmer height={28} width="50%" />
              <Shimmer height={24} width="40%" margin="12px 0 8px 0" />
            </div>
          </Col>
        </Row>
      </Card>

      {/* Price recommendations table with shimmer */}
      <Card>
        {/* Table header */}
        <div style={{ padding: '16px 0', borderBottom: '1px solid #f0f0f0' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            {columns.map((column, index) => (
              <div 
                key={`header-${index}`} 
                style={{ 
                  width: index === 0 ? '20%' : '13.3%',
                  padding: '0 8px'
                }}
              >
                <Shimmer height={16} width="80%" />
              </div>
            ))}
          </div>
        </div>

        {/* Table rows */}
        {Array.from({ length: 8 }).map((_, rowIndex) => (
          <div 
            key={`row-${rowIndex}`} 
            style={{ 
              padding: '16px 0', 
              borderBottom: '1px solid #f0f0f0',
              display: 'flex',
              justifyContent: 'space-between'
            }}
          >
            {/* Item column */}
            <div style={{ width: '20%', padding: '0 8px' }}>
              <Shimmer height={16} width="90%" margin="0 0 8px 0" />
              <Shimmer height={14} width="60%" />
            </div>
            
            {/* Current Price column */}
            <div style={{ width: '13.3%', padding: '0 8px' }}>
              <Shimmer height={16} width="60%" />
            </div>
            
            {/* Performance column */}
            <div style={{ width: '13.3%', padding: '0 8px' }}>
              <Shimmer height={16} width="80%" margin="0 0 8px 0" />
              <Shimmer height={14} width="60%" />
            </div>
            
            {/* Gross Margin column */}
            <div style={{ width: '13.3%', padding: '0 8px' }}>
              <Shimmer height={16} width="50%" />
            </div>
            
            {/* Net Margin column */}
            <div style={{ width: '13.3%', padding: '0 8px' }}>
              <Shimmer height={16} width="50%" />
            </div>
            
            {/* Recommendation column */}
            <div style={{ width: '13.3%', padding: '0 8px' }}>
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <Shimmer height={24} width={24} borderRadius="50%" margin="0 8px 0 0" />
                <Shimmer height={16} width="70%" />
              </div>
            </div>
          </div>
        ))}
      </Card>
    </>
  );
};

export const DashboardShimmerLoader: React.FC = () => (
  <>
    <ShimmerDashboardStats />
    <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
      <Col xs={24} lg={16}>
        <ShimmerChart />
      </Col>
      <Col xs={24} lg={8}>
        <ShimmerActionItems />
      </Col>
    </Row>
    <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
      <Col xs={24} lg={12}>
        <ShimmerTable rows={3} />
      </Col>
      <Col xs={24} lg={12}>
        <ShimmerProductList />
      </Col>
    </Row>
  </>
);
