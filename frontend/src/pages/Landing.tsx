import { useState } from 'react';
import { ChartBarIcon, DocumentTextIcon, LightBulbIcon, CogIcon } from '@heroicons/react/24/outline';
import { Button } from '@/components/ui/button';
import { useNavigate } from 'react-router-dom';

const features = [
  {
    name: 'AI-Powered Research',
    description: 'Deep competitor analysis using advanced AI to identify market opportunities and threats.',
    icon: ChartBarIcon,
  },
  {
    name: 'Strategic Planning',
    description: 'Generate comprehensive media strategies with budget allocation and content recommendations.',
    icon: LightBulbIcon,
  },
  {
    name: 'Automated Reports',
    description: 'Export professional PowerPoint, PDF, and Word documents with charts and insights.',
    icon: DocumentTextIcon,
  },
  {
    name: 'Real-time Intelligence',
    description: 'Access up-to-date market data and competitor intelligence from multiple sources.',
    icon: CogIcon,
  },
];

const stats = [
  { name: 'Competitors Analyzed', value: '10,000+' },
  { name: 'Markets Researched', value: '50+' },
  { name: 'Reports Generated', value: '1,000+' },
  { name: 'Success Rate', value: '95%' },
];

const Landing = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');

  const handleGetStarted = () => {
    navigate('/dashboard');
  };

  const handleSubmitEmail = (e: React.FormEvent) => {
    e.preventDefault();
    // Handle email submission for updates
    console.log('Email submitted:', email);
    setEmail('');
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Navigation */}
      <nav className="border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <h1 className="text-xl font-semibold text-primary">AI Media Research</h1>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <Button variant="ghost" onClick={() => navigate('/dashboard')}>
                Dashboard
              </Button>
              <Button onClick={handleGetStarted}>
                Get Started
              </Button>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <h1 className="text-4xl md:text-6xl font-bold text-text-primary mb-6 animate-fade-in">
              AI-Powered Media Research
              <span className="block text-primary">& Strategy Platform</span>
            </h1>
            <p className="text-xl text-text-secondary max-w-3xl mx-auto mb-10 animate-fade-in [animation-delay:200ms]">
              Automate competitor analysis, market research, and media strategy planning with AI. 
              Generate professional reports in minutes, not weeks.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center animate-fade-in [animation-delay:400ms]">
              <Button size="lg" onClick={handleGetStarted} className="px-8 py-3 transition-transform hover:scale-105">
                Start Research Now
              </Button>
              <Button variant="outline" size="lg" className="px-8 py-3 transition-transform hover:scale-105">
                View Demo
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-16 bg-surface-primary">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <dl className="grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-4">
            {stats.map((stat, index) => (
              <div key={stat.name} className="text-center animate-fade-in transition-transform hover:scale-105" style={{ animationDelay: `${index * 100}ms` }}>
                <dt className="text-base text-text-secondary">{stat.name}</dt>
                <dd className="text-3xl font-bold text-primary">{stat.value}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-text-primary mb-4">
              Everything you need for market intelligence
            </h2>
            <p className="text-lg text-text-secondary max-w-2xl mx-auto">
              From competitor identification to strategy execution, our AI platform handles the entire research workflow.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {features.map((feature, index) => (
              <div key={feature.name} className="p-6 bg-surface-primary rounded-lg border border-border animate-fade-in transition-transform hover:scale-105" style={{ animationDelay: `${index * 150}ms` }}>
                <div className="flex items-center mb-4">
                  <feature.icon className="h-6 w-6 text-primary mr-3" />
                  <h3 className="text-lg font-semibold text-text-primary">{feature.name}</h3>
                </div>
                <p className="text-text-secondary">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it Works */}
      <section className="py-20 bg-surface-primary">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-text-primary mb-4">
              Research in 3 simple steps
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="text-center animate-fade-in" style={{ animationDelay: '100ms' }}>
              <div className="w-12 h-12 bg-primary text-primary-foreground rounded-full flex items-center justify-center mx-auto mb-4 text-xl font-bold transition-transform hover:scale-110">
                1
              </div>
              <h3 className="text-lg font-semibold text-text-primary mb-2">Input Your Brand</h3>
              <p className="text-text-secondary">Enter your brand, industry, and target market details</p>
            </div>
            <div className="text-center animate-fade-in" style={{ animationDelay: '200ms' }}>
              <div className="w-12 h-12 bg-primary text-primary-foreground rounded-full flex items-center justify-center mx-auto mb-4 text-xl font-bold transition-transform hover:scale-110">
                2
              </div>
              <h3 className="text-lg font-semibold text-text-primary mb-2">AI Analysis</h3>
              <p className="text-text-secondary">Our AI researches competitors and analyzes market trends</p>
            </div>
            <div className="text-center animate-fade-in" style={{ animationDelay: '300ms' }}>
              <div className="w-12 h-12 bg-primary text-primary-foreground rounded-full flex items-center justify-center mx-auto mb-4 text-xl font-bold transition-transform hover:scale-110">
                3
              </div>
              <h3 className="text-lg font-semibold text-text-primary mb-2">Get Reports</h3>
              <p className="text-text-secondary">Download professional strategy reports and presentations</p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20">
        <div className="max-w-4xl mx-auto text-center px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-text-primary mb-4">
            Ready to revolutionize your market research?
          </h2>
          <p className="text-lg text-text-secondary mb-8">
            Join hundreds of marketers already using AI to gain competitive advantage.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-12">
            <Button size="lg" onClick={handleGetStarted} className="px-8 py-3">
              Start Free Research
            </Button>
          </div>

          {/* Email Signup */}
          <form onSubmit={handleSubmitEmail} className="max-w-md mx-auto">
            <div className="flex gap-2">
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Enter your email for updates"
                className="flex-1 px-4 py-2 bg-surface-primary border border-border rounded-md text-text-primary placeholder-text-tertiary focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <Button type="submit" variant="outline">
                Subscribe
              </Button>
            </div>
          </form>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <h3 className="text-lg font-semibold text-primary mb-4">AI Media Research</h3>
            <p className="text-text-secondary">
              © 2024 AI Media Research Platform. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Landing;