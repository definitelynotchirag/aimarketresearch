import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { ChartBarIcon, DocumentTextIcon, PlayIcon } from '@heroicons/react/24/outline';
import { WorkflowRequest } from '@/types/api';

const Dashboard = () => {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState<WorkflowRequest>({
    brand: '',
    country: '',
    industry: '',
    goals: [],
    budget_usd: 10000,
    time_horizon_months: 3,
    max_results: 10,
  });

  const handleInputChange = (field: keyof WorkflowRequest, value: any) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleGoalsChange = (goalString: string) => {
    const goals = goalString.split(',').map(g => g.trim()).filter(g => g.length > 0);
    handleInputChange('goals', goals);
  };

  const handleStartResearch = async () => {
    if (!formData.brand || !formData.industry || !formData.country) {
      alert('Please fill in all required fields');
      return;
    }

    setIsLoading(true);
    
    // Navigate to results with form data
    navigate('/results', { state: { formData } });
  };

  const goToLanding = () => {
    navigate('/');
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <h1 
              className="text-xl font-semibold text-primary cursor-pointer" 
              onClick={goToLanding}
            >
              AI Media Research
            </h1>
            <div className="flex items-center gap-4">
              <Button variant="ghost" onClick={goToLanding}>
                Home
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Page Title */}
        <div className="mb-8 animate-fade-in">
          <h1 className="text-3xl font-bold text-text-primary mb-2">Research Dashboard</h1>
          <p className="text-text-secondary">Enter your brand details to start AI-powered market research and strategy planning.</p>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card className="animate-fade-in transition-transform hover:scale-105" style={{ animationDelay: '100ms' }}>
            <CardContent className="p-6">
              <div className="flex items-center">
                <ChartBarIcon className="h-8 w-8 text-ai-blue mr-3" />
                <div>
                  <p className="text-sm text-text-secondary">Research Time</p>
                  <p className="text-2xl font-bold text-text-primary">~2 min</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="animate-fade-in transition-transform hover:scale-105" style={{ animationDelay: '200ms' }}>
            <CardContent className="p-6">
              <div className="flex items-center">
                <DocumentTextIcon className="h-8 w-8 text-ai-green mr-3" />
                <div>
                  <p className="text-sm text-text-secondary">Report Formats</p>
                  <p className="text-2xl font-bold text-text-primary">3 Types</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="animate-fade-in transition-transform hover:scale-105" style={{ animationDelay: '300ms' }}>
            <CardContent className="p-6">
              <div className="flex items-center">
                <PlayIcon className="h-8 w-8 text-primary mr-3" />
                <div>
                  <p className="text-sm text-text-secondary">Ready to Start</p>
                  <p className="text-2xl font-bold text-text-primary">Now</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Research Form */}
        <Card className="animate-fade-in" style={{ animationDelay: '400ms' }}>
          <CardHeader>
            <CardTitle>Start New Research</CardTitle>
            <CardDescription>
              Provide details about your brand and research goals. Our AI will analyze competitors, 
              market trends, and generate comprehensive strategy recommendations.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Brand Information */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="brand">Brand Name *</Label>
                <Input
                  id="brand"
                  placeholder="e.g., Tesla, Airbnb, Slack"
                  value={formData.brand}
                  onChange={(e) => handleInputChange('brand', e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="industry">Industry *</Label>
                <Input
                  id="industry"
                  placeholder="e.g., Electric Vehicles, Travel, SaaS"
                  value={formData.industry}
                  onChange={(e) => handleInputChange('industry', e.target.value)}
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="country">Target Market *</Label>
                <Select value={formData.country} onValueChange={(value) => handleInputChange('country', value)}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select target market" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="United States">United States</SelectItem>
                    <SelectItem value="Global">Global</SelectItem>
                    <SelectItem value="United Kingdom">United Kingdom</SelectItem>
                    <SelectItem value="Canada">Canada</SelectItem>
                    <SelectItem value="Germany">Germany</SelectItem>
                    <SelectItem value="France">France</SelectItem>
                    <SelectItem value="Australia">Australia</SelectItem>
                    <SelectItem value="Japan">Japan</SelectItem>
                    <SelectItem value="India">India</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="budget">Budget (USD)</Label>
                <Input
                  id="budget"
                  type="number"
                  min="1000"
                  step="1000"
                  value={formData.budget_usd}
                  onChange={(e) => handleInputChange('budget_usd', parseInt(e.target.value) || 0)}
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="timeHorizon">Time Horizon (Months)</Label>
                <Select 
                  value={formData.time_horizon_months.toString()} 
                  onValueChange={(value) => handleInputChange('time_horizon_months', parseInt(value))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="1">1 Month</SelectItem>
                    <SelectItem value="3">3 Months</SelectItem>
                    <SelectItem value="6">6 Months</SelectItem>
                    <SelectItem value="12">12 Months</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="maxResults">Max Competitors to Analyze</Label>
                <Select 
                  value={formData.max_results?.toString()} 
                  onValueChange={(value) => handleInputChange('max_results', parseInt(value))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="5">5 Competitors</SelectItem>
                    <SelectItem value="10">10 Competitors</SelectItem>
                    <SelectItem value="15">15 Competitors</SelectItem>
                    <SelectItem value="20">20 Competitors</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="goals">Marketing Goals (comma-separated)</Label>
              <Textarea
                id="goals"
                placeholder="e.g., awareness, leads, sales, retention, brand building"
                value={formData.goals.join(', ')}
                onChange={(e) => handleGoalsChange(e.target.value)}
                rows={2}
              />
            </div>

            {/* Action Buttons */}
            <div className="flex flex-col sm:flex-row gap-4 pt-4">
              <Button 
                onClick={handleStartResearch}
                disabled={isLoading}
                className="flex-1 transition-transform hover:scale-105"
                size="lg"
              >
                {isLoading ? 'Starting Research...' : 'Start AI Research'}
              </Button>
              <Button 
                variant="outline" 
                size="lg"
                className="transition-transform hover:scale-105"
                onClick={() => {
                  setFormData({
                    brand: 'Tesla',
                    country: 'United States',
                    industry: 'Electric Vehicles',
                    goals: ['awareness', 'consideration', 'leads'],
                    budget_usd: 50000,
                    time_horizon_months: 6,
                    max_results: 12,
                  });
                }}
              >
                Use Tesla Example
              </Button>
            </div>

            {/* Info Text */}
            <div className="text-sm text-text-tertiary bg-surface-secondary p-4 rounded-lg">
              <p className="mb-1"><strong>What happens next:</strong></p>
              <p>• AI analyzes your competitors and market trends</p>
              <p>• Strategic recommendations are generated</p>
              <p>• Professional reports become available for download</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Dashboard;