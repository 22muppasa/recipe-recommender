
import React, { useRef, useEffect, useState } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useGSAP } from "@gsap/react";

gsap.registerPlugin(ScrollTrigger, useGSAP);

export interface SplitTextProps {
  text: string;
  className?: string;
  delay?: number;
  duration?: number;
  ease?: string | ((t: number) => number);
  splitType?: "chars" | "words" | "lines" | "words, chars";
  from?: gsap.TweenVars;
  to?: gsap.TweenVars;
  threshold?: number;
  rootMargin?: string;
  tag?: "h1" | "h2" | "h3" | "h4" | "h5" | "h6" | "p" | "span";
  textAlign?: React.CSSProperties["textAlign"];
  onLetterAnimationComplete?: () => void;
}

const SplitText: React.FC<SplitTextProps> = ({
  text,
  className = "",
  delay = 100,
  duration = 0.6,
  ease = "power3.out",
  splitType = "chars",
  from = { opacity: 0, y: 40 },
  to = { opacity: 1, y: 0 },
  threshold = 0.1,
  rootMargin = "-100px",
  textAlign = "center",
  tag = "p",
  onLetterAnimationComplete,
}) => {
  const ref = useRef<HTMLElement>(null);
  const animationCompletedRef = useRef(false);
  const [fontsLoaded, setFontsLoaded] = useState<boolean>(false);

  useEffect(() => {
    if (document.fonts.status === "loaded") {
      setFontsLoaded(true);
    } else {
      document.fonts.ready.then(() => {
        setFontsLoaded(true);
      });
    }
  }, []);

  useGSAP(
    () => {
      if (!ref.current || !text || !fontsLoaded) return;

      const el = ref.current;
      const chars = text.split('');
      
      // Clear existing content and create spans for each character
      el.innerHTML = '';
      chars.forEach((char) => {
        const span = document.createElement('span');
        span.textContent = char === ' ' ? '\u00A0' : char;
        span.className = 'split-char';
        el.appendChild(span);
      });

      const charElements = el.querySelectorAll('.split-char');
      
      // Set initial state
      gsap.set(charElements, from);

      // Create scroll trigger animation
      gsap.to(charElements, {
        ...to,
        duration,
        ease,
        stagger: delay / 1000,
        scrollTrigger: {
          trigger: el,
          start: `top ${(1 - threshold) * 100}%`,
          once: true,
        },
        onComplete: () => {
          animationCompletedRef.current = true;
          onLetterAnimationComplete?.();
        },
      });

    },
    {
      dependencies: [
        text,
        delay,
        duration,
        ease,
        splitType,
        JSON.stringify(from),
        JSON.stringify(to),
        threshold,
        rootMargin,
        fontsLoaded,
        onLetterAnimationComplete,
      ],
      scope: ref,
    }
  );

  const style: React.CSSProperties = {
    textAlign,
    overflow: "visible",
    display: "inline-block",
    whiteSpace: "normal",
    wordWrap: "break-word",
    willChange: "transform, opacity",
  };

  const classes = `split-parent ${className}`;

  // Create the appropriate element based on the tag prop
  const createElement = () => {
    const props = {
      ref: ref as React.RefObject<any>,
      style,
      className: classes,
      children: text
    };

    switch (tag) {
      case "h1":
        return React.createElement("h1", props);
      case "h2":
        return React.createElement("h2", props);
      case "h3":
        return React.createElement("h3", props);
      case "h4":
        return React.createElement("h4", props);
      case "h5":
        return React.createElement("h5", props);
      case "h6":
        return React.createElement("h6", props);
      case "span":
        return React.createElement("span", props);
      default:
        return React.createElement("p", props);
    }
  };

  return createElement();
};

export default SplitText;
