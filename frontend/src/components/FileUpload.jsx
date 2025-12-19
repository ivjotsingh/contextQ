import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileText, X, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';

const ACCEPTED_TYPES = {
  'application/pdf': ['.pdf'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
  'text/plain': ['.txt'],
};

const MAX_SIZE = 10 * 1024 * 1024; // 10MB

export function FileUpload({ onUpload, isUploading, uploadProgress }) {
  const [uploadStatus, setUploadStatus] = useState([]); // { file, status, message }

  const onDrop = useCallback(
    async (acceptedFiles, rejectedFiles) => {
      // Handle rejected files
      const rejected = rejectedFiles.map(({ file, errors }) => ({
        file: file.name,
        status: 'error',
        message: errors[0]?.message || 'File rejected',
      }));

      setUploadStatus(rejected);

      // Upload accepted files
      if (acceptedFiles.length > 0 && onUpload) {
        const results = await onUpload(acceptedFiles);
        
        const statuses = results.map(result => ({
          file: result.file,
          status: result.success ? 'success' : 'error',
          message: result.isDuplicate 
            ? 'Already uploaded' 
            : result.success 
              ? 'Uploaded successfully' 
              : result.error,
        }));

        setUploadStatus(prev => [...prev, ...statuses]);

        // Clear status after 3 seconds
        setTimeout(() => setUploadStatus([]), 3000);
      }
    },
    [onUpload]
  );

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    maxSize: MAX_SIZE,
    multiple: true,
  });

  return (
    <div className="space-y-4">
      <div
        {...getRootProps()}
        className={`upload-zone ${
          isDragActive && !isDragReject ? 'upload-zone-active' : ''
        } ${isDragReject ? 'border-red-500/50 bg-red-500/5' : ''}`}
      >
        <input {...getInputProps()} />

        {isUploading ? (
          <div className="flex flex-col items-center gap-4">
            <div className="relative">
              <Loader2 className="w-12 h-12 text-sky-500 animate-spin" />
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-xs font-medium text-sky-400">
                  {Math.round(uploadProgress)}%
                </span>
              </div>
            </div>
            <p className="text-gray-400">Processing document...</p>
          </div>
        ) : (
          <>
            <div className="w-16 h-16 rounded-2xl bg-sky-500/10 flex items-center justify-center mb-2">
              <Upload className="w-8 h-8 text-sky-400" />
            </div>
            
            <div>
              <p className="text-gray-200 font-medium mb-1">
                {isDragActive ? 'Drop files here' : 'Drop files or click to upload'}
              </p>
              <p className="text-sm text-gray-500">
                PDF, DOCX, or TXT files up to 10MB
              </p>
            </div>
          </>
        )}
      </div>

      {/* Upload status messages */}
      {uploadStatus.length > 0 && (
        <div className="space-y-2 animate-in">
          {uploadStatus.map((item, index) => (
            <div
              key={index}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm ${
                item.status === 'success'
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                  : 'bg-red-500/10 text-red-400 border border-red-500/20'
              }`}
            >
              {item.status === 'success' ? (
                <CheckCircle className="w-4 h-4 flex-shrink-0" />
              ) : (
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
              )}
              <span className="truncate">{item.file}</span>
              <span className="text-gray-500 ml-auto flex-shrink-0">{item.message}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default FileUpload;

