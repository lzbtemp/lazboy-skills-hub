import { Wrench } from 'lucide-react';
import { motion } from 'motion/react';
import type { FlatTool } from '../../types';
import ToolCard from './ToolCard';

interface Props {
  tools: FlatTool[];
}

const containerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.06 } },
};

const itemVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.22, 1, 0.36, 1] } },
};

export default function ToolGrid({ tools }: Props) {
  if (tools.length === 0) {
    return (
      <div className="text-center py-20 animate-fade-in">
        <div className="w-16 h-16 rounded-2xl bg-[#1B3A6B]/5 flex items-center justify-center mx-auto mb-5">
          <Wrench className="w-8 h-8 text-[#1B3A6B]/20" />
        </div>
        <p className="text-lg font-medium text-[#2C2C2C]/40 mb-1">No tools found</p>
        <p className="text-sm text-[#2C2C2C]/25">Try adjusting your search or filters</p>
      </div>
    );
  }

  return (
    <motion.div
      key={tools.map((t) => `${t.serverSlug}-${t.name}`).join(',')}
      className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5"
      initial="hidden"
      animate="visible"
      variants={containerVariants}
    >
      {tools.map((tool) => (
        <motion.div key={`${tool.serverSlug}-${tool.name}`} variants={itemVariants}>
          <ToolCard tool={tool} />
        </motion.div>
      ))}
    </motion.div>
  );
}
