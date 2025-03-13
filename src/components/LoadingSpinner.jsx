export default function LoadingSpinner() {
  return (
    <div className="flex flex-col items-center justify-center py-10">
      <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-teal-500 mb-4"></div>
      <p className="text-gray-600">Analyzing job posting...</p>
    </div>
  );
}