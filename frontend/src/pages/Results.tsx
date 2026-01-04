import { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  ChartBarIcon, 
  DocumentTextIcon, 
  ArrowDownTrayIcon, 
  ClockIcon,
  ExclamationTriangleIcon 
} from '@heroicons/react/24/outline';
import { ApiService } from '@/services/api';
import { WorkflowRequest, WorkflowResponse, ResearchResponse, StrategyResponse } from '@/types/api';
import { formatCurrency, downloadFile } from '@/utils/download';
import { useToast } from '@/hooks/use-toast';

const Results = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { toast } = useToast();
  
  const [isLoading, setIsLoading] = useState(true);
  const [progress, setProgress] = useState(0);
  const [data, setData] = useState<WorkflowResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isGeneratingReport, setIsGeneratingReport] = useState<string | null>(null);

  const formData = location.state?.formData as WorkflowRequest;

  useEffect(() => {
    if (!formData) {
      navigate('/dashboard');
      return;
    }
    performResearch();
  }, [formData, navigate]);

  const performResearch = async () => {
    try {
      setIsLoading(true);
      setProgress(10);

      // Simulate progress updates
      const progressInterval = setInterval(() => {
        setProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 2000);

      const result = await ApiService.runWorkflow(formData);
      
      clearInterval(progressInterval);
      setProgress(100);
      setData(result);
      
      toast({
        title: "Research Completed",
        description: "Your AI research and strategy analysis is ready!",
      });
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to perform research');
      toast({
        title: "Research Failed",
        description: "There was an error performing the research. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const generateReport = async (type: 'pptx' | 'pdf' | 'docx') => {
    if (!data) return;

    try {
      setIsGeneratingReport(type);
      
      const reportRequest = {
        brand: formData.brand,
        language: 'en',
        use_cache: true,
        research: data.research,
        strategy: data.strategy,
      };

      let blob: Blob;
      let filename: string;
      let mimeType: string;

      switch (type) {
        case 'pptx':
          blob = await ApiService.generatePPTX(reportRequest);
          filename = `${formData.brand}_Strategy_Report.pptx`;
          mimeType = 'application/vnd.openxmlformats-officedocument.presentationml.presentation';
          break;
        case 'pdf':
          blob = await ApiService.generatePDF(reportRequest);
          filename = `${formData.brand}_Research_Report.pdf`;
          mimeType = 'application/pdf';
          break;
        case 'docx':
          blob = await ApiService.generateDOCX(reportRequest);
          filename = `${formData.brand}_Analysis_Report.docx`;
          mimeType = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
          break;
      }

      downloadFile(blob, filename, mimeType);
      
      toast({
        title: "Report Downloaded",
        description: `Your ${type.toUpperCase()} report has been downloaded successfully.`,
      });
      
    } catch (err) {
      toast({
        title: "Download Failed",
        description: `Failed to generate ${type.toUpperCase()} report. Please try again.`,
        variant: "destructive",
      });
    } finally {
      setIsGeneratingReport(null);
    }
  };

  if (!formData) {
    return null;
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Card className="max-w-md mx-auto">
          <CardHeader>
            <CardTitle className="flex items-center text-error">
              <ExclamationTriangleIcon className="h-5 w-5 mr-2" />
              Research Failed
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-text-secondary mb-4">{error}</p>
            <div className="flex gap-2">
              <Button onClick={() => navigate('/dashboard')}>
                Try Again
              </Button>
              <Button variant="outline" onClick={() => navigate('/')}>
                Go Home
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <h1 
              className="text-xl font-semibold text-primary cursor-pointer" 
              onClick={() => navigate('/')}
            >
              AI Media Research
            </h1>
            <div className="flex items-center gap-4">
              <Button variant="ghost" onClick={() => navigate('/dashboard')}>
                New Research
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Loading State */}
        {isLoading && (
          <div className="max-w-2xl mx-auto">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <ClockIcon className="h-5 w-5 mr-2 text-primary" />
                  Analyzing {formData.brand}
                </CardTitle>
                <CardDescription>
                  Our AI is researching competitors and generating strategy recommendations...
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Progress value={progress} className="mb-4" />
                <p className="text-sm text-text-secondary">
                  {progress < 30 && "Identifying competitors..."}
                  {progress >= 30 && progress < 60 && "Analyzing market trends..."}
                  {progress >= 60 && progress < 90 && "Generating strategy recommendations..."}
                  {progress >= 90 && "Finalizing results..."}
                </p>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Results */}
        {data && (
          <>
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
              <Card className="animate-fade-in transition-transform hover:scale-105" style={{ animationDelay: '100ms' }}>
                <CardContent className="p-6">
                  <div className="flex items-center">
                    <ChartBarIcon className="h-8 w-8 text-ai-blue mr-3" />
                    <div>
                      <p className="text-sm text-text-secondary">Competitors Found</p>
                      <p className="text-2xl font-bold text-text-primary">{data.research.competitors.length}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
              <Card className="animate-fade-in transition-transform hover:scale-105" style={{ animationDelay: '200ms' }}>
                <CardContent className="p-6">
                  <div className="flex items-center">
                    <DocumentTextIcon className="h-8 w-8 text-ai-green mr-3" />
                    <div>
                      <p className="text-sm text-text-secondary">Market Trends</p>
                      <p className="text-2xl font-bold text-text-primary">{data.research.trends.length}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
              <Card className="animate-fade-in transition-transform hover:scale-105" style={{ animationDelay: '300ms' }}>
                <CardContent className="p-6">
                  <div>
                    <p className="text-sm text-text-secondary">Total Budget</p>
                    <p className="text-2xl font-bold text-text-primary">{formatCurrency(data.strategy.total_budget_usd)}</p>
                  </div>
                </CardContent>
              </Card>
              <Card className="animate-fade-in transition-transform hover:scale-105" style={{ animationDelay: '400ms' }}>
                <CardContent className="p-6">
                  <div>
                    <p className="text-sm text-text-secondary">Media Channels</p>
                    <p className="text-2xl font-bold text-text-primary">{Object.keys(data.strategy.allocations).length}</p>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Download Reports */}
            <Card className="mb-8 animate-fade-in" style={{ animationDelay: '500ms' }}>
              <CardHeader>
                <CardTitle>Download Reports</CardTitle>
                <CardDescription>
                  Export your research and strategy analysis in multiple formats
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <Button 
                    onClick={() => generateReport('pptx')}
                    disabled={isGeneratingReport === 'pptx'}
                    className="flex items-center justify-center transition-transform hover:scale-105"
                  >
                    <ArrowDownTrayIcon className="h-4 w-4 mr-2" />
                    {isGeneratingReport === 'pptx' ? 'Generating...' : 'PowerPoint'}
                  </Button>
                  <Button 
                    onClick={() => generateReport('pdf')}
                    disabled={isGeneratingReport === 'pdf'}
                    variant="outline"
                    className="flex items-center justify-center transition-transform hover:scale-105"
                  >
                    <ArrowDownTrayIcon className="h-4 w-4 mr-2" />
                    {isGeneratingReport === 'pdf' ? 'Generating...' : 'PDF Report'}
                  </Button>
                  <Button 
                    onClick={() => generateReport('docx')}
                    disabled={isGeneratingReport === 'docx'}
                    variant="outline"
                    className="flex items-center justify-center transition-transform hover:scale-105"
                  >
                    <ArrowDownTrayIcon className="h-4 w-4 mr-2" />
                    {isGeneratingReport === 'docx' ? 'Generating...' : 'Word Document'}
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Detailed Results */}
            <Tabs defaultValue="research" className="space-y-6 animate-fade-in" style={{ animationDelay: '600ms' }}>
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="research">Market Research</TabsTrigger>
                <TabsTrigger value="strategy">Media Strategy</TabsTrigger>
                <TabsTrigger value="analysis">SWOT Analysis</TabsTrigger>
              </TabsList>

              <TabsContent value="research" className="space-y-6">
                <ResearchTab research={data.research} />
              </TabsContent>

              <TabsContent value="strategy" className="space-y-6">
                <StrategyTab strategy={data.strategy} />
              </TabsContent>

              <TabsContent value="analysis" className="space-y-6">
                <SWOTTab swot={data.strategy.swot} />
              </TabsContent>
            </Tabs>
          </>
        )}
      </div>
    </div>
  );
};

// Research Tab Component
const ResearchTab = ({ research }: { research: ResearchResponse }) => (
  <div className="space-y-6">
    <Card>
      <CardHeader>
        <CardTitle>Executive Summary</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-text-secondary">{research.summary}</p>
      </CardContent>
    </Card>

    <Card>
      <CardHeader>
        <CardTitle>Competitors ({research.competitors.length})</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {research.competitors.map((competitor, index) => (
            <div key={index} className="p-4 border border-border rounded-lg animate-fade-in transition-transform hover:scale-105" style={{ animationDelay: `${index * 100}ms` }}>
              <h4 className="font-semibold text-text-primary mb-2">{competitor.name}</h4>
              <p className="text-sm text-text-secondary mb-2">{competitor.summary}</p>
              <a 
                href={competitor.website} 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-xs text-primary hover:underline transition-colors"
              >
                {competitor.website}
              </a>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>

    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <Card>
        <CardHeader>
          <CardTitle>Market Trends</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {research.trends.map((trend, index) => (
              <div key={index} className="flex items-start">
                <div className="w-2 h-2 bg-primary rounded-full mt-2 mr-3 flex-shrink-0" />
                <p className="text-sm text-text-secondary">{trend}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Ad Insights</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {research.ad_insights.map((insight, index) => (
              <div key={index} className="flex items-start">
                <div className="w-2 h-2 bg-ai-green rounded-full mt-2 mr-3 flex-shrink-0" />
                <p className="text-sm text-text-secondary">{insight}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  </div>
);

// Strategy Tab Component
const StrategyTab = ({ strategy }: { strategy: StrategyResponse }) => (
  <div className="space-y-6">
    <Card>
      <CardHeader>
        <CardTitle>Budget Allocation</CardTitle>
        <CardDescription>
          Total Budget: {formatCurrency(strategy.total_budget_usd)}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {Object.entries(strategy.allocations).map(([channel, amount]) => (
            <div key={channel} className="flex items-center justify-between p-3 bg-surface-secondary rounded-lg">
              <span className="font-medium text-text-primary">{channel}</span>
              <span className="text-primary font-semibold">{formatCurrency(amount)}</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>

    <Card>
      <CardHeader>
        <CardTitle>Content Strategy</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {Object.entries(strategy.content_plan).map(([type, plan]) => (
            <div key={type} className="p-4 border border-border rounded-lg">
              <h4 className="font-semibold text-text-primary mb-2">{type}</h4>
              <p className="text-sm text-text-secondary mb-2">
                {plan.cadence_per_week} times per week
              </p>
              <div className="flex flex-wrap gap-1">
                {plan.platforms.map((platform, index) => (
                  <Badge key={index} variant="secondary" className="text-xs">
                    {platform}
                  </Badge>
                ))}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>

    <Card>
      <CardHeader>
        <CardTitle>Key Performance Indicators</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap gap-2">
          {strategy.kpis.map((kpi, index) => (
            <Badge key={index} variant="outline" className="text-sm">
              {kpi}
            </Badge>
          ))}
        </div>
      </CardContent>
    </Card>
  </div>
);

// SWOT Tab Component
const SWOTTab = ({ swot }: { swot: any }) => (
  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
    <Card>
      <CardHeader>
        <CardTitle className="text-ai-green">Strengths</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {swot.strengths.map((item: string, index: number) => (
            <div key={index} className="flex items-start">
              <div className="w-2 h-2 bg-ai-green rounded-full mt-2 mr-3 flex-shrink-0" />
              <p className="text-sm text-text-secondary">{item}</p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>

    <Card>
      <CardHeader>
        <CardTitle className="text-ai-red">Weaknesses</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {swot.weaknesses.map((item: string, index: number) => (
            <div key={index} className="flex items-start">
              <div className="w-2 h-2 bg-ai-red rounded-full mt-2 mr-3 flex-shrink-0" />
              <p className="text-sm text-text-secondary">{item}</p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>

    <Card>
      <CardHeader>
        <CardTitle className="text-ai-blue">Opportunities</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {swot.opportunities.map((item: string, index: number) => (
            <div key={index} className="flex items-start">
              <div className="w-2 h-2 bg-ai-blue rounded-full mt-2 mr-3 flex-shrink-0" />
              <p className="text-sm text-text-secondary">{item}</p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>

    <Card>
      <CardHeader>
        <CardTitle className="text-warning">Threats</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {swot.threats.map((item: string, index: number) => (
            <div key={index} className="flex items-start">
              <div className="w-2 h-2 bg-warning rounded-full mt-2 mr-3 flex-shrink-0" />
              <p className="text-sm text-text-secondary">{item}</p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  </div>
);

export default Results;