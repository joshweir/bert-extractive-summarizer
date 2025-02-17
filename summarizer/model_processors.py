from summarizer.BertParent import BertParent
from typing import List
from summarizer.ClusterFeatures import ClusterFeatures
from abc import abstractmethod
import neuralcoref
from spacy.lang.en import English
import json


class ModelProcessor(object):

  def __init__(self,
               model='bert-large-uncased',
               hidden: int = -2,
               reduce_option: str = 'mean',
               greedyness: float = 0.45):
    self.model = BertParent(model)
    self.hidden = hidden
    self.reduce_option = reduce_option
    self.nlp = English()
    self.nlp.add_pipe(self.nlp.create_pipe('sentencizer'))
    neuralcoref.add_to_pipe(self.nlp, greedyness=greedyness)

  def process_content_sentences(self, body: str, min_length=40,
                                max_length=600) -> List[str]:
    doc = self.nlp(body)._.coref_resolved
    doc = self.nlp(doc)
    return [
        c.string.strip()
        for c in doc.sents
        if len(c.string.strip()) > min_length and
        len(c.string.strip()) < max_length
    ]

  @abstractmethod
  def run_clusters(self,
                   content: List[str],
                   ratio=0.2,
                   algorithm='kmeans',
                   use_first: bool = True) -> List[str]:
    raise NotImplementedError("Must Implement run_clusters")

  def calculate_ratio_from_num_sentences(self, total_sentences: int,
                                         num_sentences: int) -> float:
    if total_sentences <= 0:
      return 1.0
    if total_sentences > num_sentences * 2:
      num_sentences = num_sentences - 1
    ratio = num_sentences / total_sentences
    if ratio > 1:
      ratio = 1.0
    return ratio

  def run(self,
          body: str,
          result_format: str = 'text',
          num_sentences: int = 0,
          ratio: float = 0.2,
          min_length: int = 40,
          max_length: int = 600,
          use_first: bool = True,
          algorithm='kmeans') -> str:
    sentences = self.process_content_sentences(body, min_length, max_length)
    if sentences:
      if num_sentences > 0:
        ratio = self.calculate_ratio_from_num_sentences(
            len(sentences), num_sentences)
      sentences = self.run_clusters(sentences, ratio, algorithm, use_first)
    if result_format == 'array':
      return json.dumps(sentences)
    return ' '.join(sentences)

  def __call__(self,
               body: str,
               result_format: str = 'text',
               num_sentences: int = 0,
               ratio: float = 0.2,
               min_length: int = 40,
               max_length: int = 600,
               use_first: bool = True,
               algorithm='kmeans') -> str:
    return self.run(body, result_format, num_sentences, ratio, min_length,
                    max_length)


class SingleModel(ModelProcessor):
  """
    Deprecated for naming sake.
    """

  def __init__(self,
               model='bert-large-uncased',
               hidden: int = -2,
               reduce_option: str = 'mean',
               greedyness: float = 0.45):
    super(SingleModel, self).__init__(model, hidden, reduce_option, greedyness)

  def run_clusters(self,
                   content: List[str],
                   ratio=0.2,
                   algorithm='kmeans',
                   use_first: bool = True) -> List[str]:
    hidden = self.model(content, self.hidden, self.reduce_option)
    hidden_args = ClusterFeatures(hidden, algorithm).cluster(ratio)
    if use_first:
      if hidden_args[0] != 0:
        hidden_args.insert(0, 0)
    return [content[j] for j in hidden_args]


class Summarizer(SingleModel):

  def __init__(self,
               model='bert-large-uncased',
               hidden: int = -2,
               reduce_option: str = 'mean',
               greedyness: float = 0.45):
    super(Summarizer, self).__init__(model, hidden, reduce_option, greedyness)
