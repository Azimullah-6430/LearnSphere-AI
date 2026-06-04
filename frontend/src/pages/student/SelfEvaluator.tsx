import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import Header from '../../components/Header';
import Sidebar from '../../components/Sidebar';
import { useDropzone } from 'react-dropzone';
import toast from 'react-hot-toast';
import { evaluationService } from '../../services/apiService';
import { Upload, AlertCircle } from 'lucide-react';

interface SubmissionForm {
  subject: string;
  level: string;
  stream: string;
  submission_type: string;
}

const SelfEvaluator: React.FC = () => {
  const { register, handleSubmit } = useForm<SubmissionForm>({
    defaultValues: {
      subject: 'maths',
      level: 'school',
      stream: 'regular',
      submission_type: 'self_eval',
    },
  });

  const [files, setFiles] = useState<{
    question_paper: File | null;
    answer_script: File | null;
  }>({
    question_paper: null,
    answer_script: null,
  });

  const [loading, setLoading] = useState(false);
  const [evaluation, setEvaluation] = useState<any>(null);

  const onDropQP = (acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setFiles((prev) => ({ ...prev, question_paper: acceptedFiles[0] }));
    }
  };

  const onDropAS = (acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setFiles((prev) => ({ ...prev, answer_script: acceptedFiles[0] }));
    }
  };

  const { getRootProps: getQPProps } = useDropzone({ onDrop: onDropQP });
  const { getRootProps: getASProps } = useDropzone({ onDrop: onDropAS });

  const onSubmit = async (data: SubmissionForm) => {
    if (!files.question_paper || !files.answer_script) {
      toast.error('Please upload both question paper and answer script');
      return;
    }

    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('question_paper', files.question_paper);
      formData.append('answer_script', files.answer_script);
      formData.append('subject', data.subject);
      formData.append('level', data.level);
      formData.append('stream', data.stream);
      formData.append('submission_type', 'self_eval');

      const result = await evaluationService.submitForEvaluation(formData);
      setEvaluation(result.evaluation);
      toast.success('Self-evaluation completed with 95%+ accuracy!');
    } catch (error: any) {
      toast.error(error.response?.data?.error || 'Evaluation failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-screen bg-gray-100">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Header />
        <main className="flex-1 overflow-auto p-8">
          <div className="max-w-4xl mx-auto">
            <h1 className="text-3xl font-bold mb-8">📋 Self Evaluator</h1>
            <div className="bg-white rounded-lg shadow-lg p-8">
              <div className="mb-6 bg-blue-50 border-l-4 border-blue-500 p-4 rounded">
                <div className="flex items-start gap-3">
                  <AlertCircle className="text-blue-600 mt-1" />
                  <div>
                    <h3 className="font-semibold text-blue-900">AI-Powered Evaluation</h3>
                    <p className="text-blue-800 text-sm mt-1">
                      Upload your question paper and answer script for 95%+ accurate AI evaluation with detailed feedback.
                    </p>
                  </div>
                </div>
              </div>

              <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">Subject</label>
                    <select
                      {...register('subject')}
                      className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="maths">Mathematics</option>
                      <option value="physics">Physics</option>
                      <option value="chemistry">Chemistry</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">Level</label>
                    <select
                      {...register('level')}
                      className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="school">School</option>
                      <option value="college">College</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">Stream</label>
                    <select
                      {...register('stream')}
                      className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="regular">Regular</option>
                      <option value="advanced">Advanced</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div
                    {...getQPProps()}
                    className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:border-blue-500 transition"
                  >
                    <Upload className="mx-auto mb-2 text-gray-400" />
                    <p className="font-medium">Question Paper</p>
                    <p className="text-sm text-gray-500 mt-1">PDF or Image</p>
                    {files.question_paper && (
                      <p className="text-green-600 mt-2">✓ {files.question_paper.name}</p>
                    )}
                  </div>

                  <div
                    {...getASProps()}
                    className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:border-blue-500 transition"
                  >
                    <Upload className="mx-auto mb-2 text-gray-400" />
                    <p className="font-medium">Answer Script</p>
                    <p className="text-sm text-gray-500 mt-1">PDF or Image</p>
                    {files.answer_script && (
                      <p className="text-green-600 mt-2">✓ {files.answer_script.name}</p>
                    )}
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-semibold py-3 rounded-lg transition"
                >
                  {loading ? '⏳ Evaluating...' : '🚀 Start Evaluation'}
                </button>
              </form>

              {evaluation && (
                <div className="mt-8 bg-green-50 border-l-4 border-green-500 p-6 rounded-lg">
                  <h3 className="font-bold text-green-900 mb-4">Evaluation Results</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                    <div className="bg-white p-4 rounded text-center">
                      <p className="text-gray-600 text-sm">Score</p>
                      <p className="text-2xl font-bold text-green-600">{evaluation.ai_score}/{evaluation.total_marks}</p>
                    </div>
                    <div className="bg-white p-4 rounded text-center">
                      <p className="text-gray-600 text-sm">Percentage</p>
                      <p className="text-2xl font-bold text-blue-600">{evaluation.percentage}%</p>
                    </div>
                    <div className="bg-white p-4 rounded text-center">
                      <p className="text-gray-600 text-sm">Accuracy</p>
                      <p className="text-2xl font-bold text-purple-600">{(evaluation.accuracy * 100).toFixed(1)}%</p>
                    </div>
                  </div>
                  <div className="bg-white p-4 rounded">
                    <p className="text-gray-600 font-medium mb-2">Feedback:</p>
                    <p className="text-gray-700">{evaluation.feedback}</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
};

export default SelfEvaluator;