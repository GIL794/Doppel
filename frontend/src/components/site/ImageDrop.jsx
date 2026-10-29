import { useRef, useState } from "react";
import { toast } from "sonner";
import { uploadImage, formatApiError } from "@/lib/api";

export const ImageDrop = ({ kind, label, value, onChange, testId }) => {
  const inputRef = useRef(null);
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(false);

  const handle = async (file) => {
    if (!file) return;
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      toast.error("Please choose a JPG, PNG or WEBP image");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      toast.error("Image must be under 10 MB");
      return;
    }
    setBusy(true);
    setPreview(URL.createObjectURL(file));
    try {
      const data = await uploadImage(file, kind);
      onChange(data.file_id);
    } catch (e) {
      setPreview(null);
      onChange(null);
      toast.error(formatApiError(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <button
      type="button"
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => { e.preventDefault(); handle(e.dataTransfer.files?.[0]); }}
      className="w-full border-2 border-dashed border-ink bg-white hover:bg-blush/40 transition-colors p-3 flex items-center gap-3 text-left"
      data-testid={testId}
    >
      <div className="w-14 h-14 shrink-0 border-2 border-ink bg-ground overflow-hidden flex items-center justify-center">
        {preview ? <img src={preview} alt="" className="w-full h-full object-cover" /> : <span className="dsp text-2xl">+</span>}
      </div>
      <div className="min-w-0">
        <p className="lab">{label}</p>
        <p className="text-sm text-graphite truncate">
          {busy ? "Uploading…" : value ? "Uploaded ✓ · tap to replace" : "Tap or drop an image"}
        </p>
      </div>
      <input ref={inputRef} type="file" accept="image/jpeg,image/png,image/webp" className="hidden"
        onChange={(e) => handle(e.target.files?.[0])} data-testid={`${testId}-input`} />
    </button>
  );
};
