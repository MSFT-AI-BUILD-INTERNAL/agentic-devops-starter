// MarkdownContent component for rendering markdown in chat messages
import { memo } from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MarkdownContentProps {
  content: string;
  className?: string;
}

export const MarkdownContent = memo(({ content, className = '' }: MarkdownContentProps) => {
  return (
    <div className={`markdown-content ${className}`}>
      <Markdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => <h1 className="text-xl font-bold mt-3 mb-2">{children}</h1>,
          h2: ({ children }) => <h2 className="text-lg font-bold mt-3 mb-1">{children}</h2>,
          h3: ({ children }) => <h3 className="text-base font-semibold mt-2 mb-1">{children}</h3>,
          p: ({ children }) => <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>,
          ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>,
          ol: ({ children }) => (
            <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>
          ),
          li: ({ children }) => <li className="leading-relaxed">{children}</li>,
          code: ({ inline, children, ...props }: { inline?: boolean; children?: React.ReactNode }) =>
            inline ? (
              <code
                className="px-1 py-0.5 rounded text-sm font-mono bg-black bg-opacity-10"
                {...props}
              >
                {children}
              </code>
            ) : (
              <code className="block" {...props}>
                {children}
              </code>
            ),
          pre: ({ children }) => (
            <pre className="p-3 rounded-md text-sm font-mono overflow-x-auto mb-2 bg-black bg-opacity-10">
              {children}
            </pre>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-l-4 border-current border-opacity-30 pl-3 italic mb-2">
              {children}
            </blockquote>
          ),
          a: ({ href, children }) => {
            // Only allow safe protocols to prevent javascript: / data: URI injection
            const safeHref =
              href && /^https?:\/\//i.test(href) ? href : undefined;
            return (
              <a
                href={safeHref}
                target="_blank"
                rel="noopener noreferrer"
                className="underline opacity-80 hover:opacity-100"
              >
                {children}
              </a>
            );
          },
          table: ({ children }) => (
            <div className="overflow-x-auto mb-2">
              <table className="min-w-full border-collapse text-sm">{children}</table>
            </div>
          ),
          th: ({ children }) => (
            <th className="border border-current border-opacity-30 px-3 py-1 font-semibold text-left">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border border-current border-opacity-30 px-3 py-1">{children}</td>
          ),
          hr: () => <hr className="border-current border-opacity-20 my-3" />,
          strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
          em: ({ children }) => <em className="italic">{children}</em>,
        }}
      >
        {content}
      </Markdown>
    </div>
  );
});

MarkdownContent.displayName = 'MarkdownContent';
