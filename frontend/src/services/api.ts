import axios from 'axios';
import {
  ResearchRequest,
  ResearchResponse,
  StrategyRequest,
  StrategyResponse,
  WorkflowRequest,
  WorkflowResponse,
  ReportGenerationRequest,
  ApiError
} from '@/types/api';

// Configure axios defaults
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const API_KEY = import.meta.env.VITE_API_KEY || 'your-api-key-here';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'x-api-key': API_KEY,
  },
  timeout: 120000, // 2 minutes timeout for AI processing
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.data) {
      throw new Error(error.response.data.detail || 'API Error');
    }
    throw new Error(error.message || 'Network Error');
  }
);

export class ApiService {
  static async healthCheck(): Promise<{ status: string }> {
    const response = await api.get('/health');
    return response.data;
  }

  static async performResearch(request: ResearchRequest): Promise<ResearchResponse> {
    const response = await api.post('/api/research', request);
    return response.data;
  }

  static async createStrategy(request: StrategyRequest): Promise<StrategyResponse> {
    const response = await api.post('/api/strategy', request);
    return response.data;
  }

  static async runWorkflow(request: WorkflowRequest): Promise<WorkflowResponse> {
    const response = await api.post('/api/workflow', request);
    return response.data;
  }

  static async generatePPTX(request: ReportGenerationRequest): Promise<Blob> {
    const response = await api.post('/api/generate/pptx', request, {
      responseType: 'blob',
    });
    return response.data;
  }

  static async generatePDF(request: ReportGenerationRequest): Promise<Blob> {
    const response = await api.post('/api/generate/pdf', request, {
      responseType: 'blob',
    });
    return response.data;
  }

  static async generateDOCX(request: ReportGenerationRequest): Promise<Blob> {
    const response = await api.post('/api/generate/docx', request, {
      responseType: 'blob',
    });
    return response.data;
  }
}

export default ApiService;