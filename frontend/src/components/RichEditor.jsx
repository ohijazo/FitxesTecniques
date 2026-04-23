import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Underline from '@tiptap/extension-underline';
import { useEffect } from 'react';

function ToolbarButton({ active, onClick, title, children }) {
  return (
    <button
      type="button"
      className={`rich-tb-btn ${active ? 'active' : ''}`}
      onClick={onClick}
      title={title}
    >
      {children}
    </button>
  );
}

export default function RichEditor({ value, onChange, compact }) {
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: false,
        codeBlock: false,
        blockquote: false,
        horizontalRule: false,
        code: false,
      }),
      Underline,
    ],
    content: value || '',
    onUpdate: ({ editor }) => {
      onChange(editor.getHTML());
    },
  });

  // Sincronitzar si el valor extern canvia (ex: càrrega inicial)
  useEffect(() => {
    if (editor && value !== undefined && editor.getHTML() !== value) {
      editor.commands.setContent(value || '', false);
    }
  }, [value]);

  if (!editor) return null;

  return (
    <div className={`rich-editor ${compact ? 'rich-editor-compact' : ''}`}>
      <div className="rich-toolbar">
        <ToolbarButton active={editor.isActive('bold')} onClick={() => editor.chain().focus().toggleBold().run()} title="Negreta (Ctrl+B)">
          <strong>N</strong>
        </ToolbarButton>
        <ToolbarButton active={editor.isActive('italic')} onClick={() => editor.chain().focus().toggleItalic().run()} title="Cursiva (Ctrl+I)">
          <em>C</em>
        </ToolbarButton>
        <ToolbarButton active={editor.isActive('underline')} onClick={() => editor.chain().focus().toggleUnderline().run()} title="Subratllat (Ctrl+U)">
          <span style={{ textDecoration: 'underline' }}>S</span>
        </ToolbarButton>
        {!compact && (
          <>
            <span className="rich-tb-sep" />
            <ToolbarButton active={editor.isActive('bulletList')} onClick={() => editor.chain().focus().toggleBulletList().run()} title="Llista">
              &#8226;
            </ToolbarButton>
            <ToolbarButton active={editor.isActive('orderedList')} onClick={() => editor.chain().focus().toggleOrderedList().run()} title="Llista numerada">
              1.
            </ToolbarButton>
          </>
        )}
        <span className="rich-tb-sep" />
        <ToolbarButton onClick={() => editor.chain().focus().clearNodes().unsetAllMarks().run()} title="Netejar format">
          Tx
        </ToolbarButton>
      </div>
      <EditorContent editor={editor} className="rich-content" />
    </div>
  );
}
